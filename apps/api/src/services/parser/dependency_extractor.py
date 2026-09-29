import ast
from typing import Any

from apps.api.src.models.enums import DependencyType


class ExtractedDependency:
    def __init__(
        self,
        raw_target: str,
        dependency_type: DependencyType,
        line_number: int,
        is_relative: bool = False,
    ):
        self.raw_target = raw_target
        self.dependency_type = dependency_type
        self.line_number = line_number
        self.is_relative = is_relative


def _clean_str(text: str) -> str:
    return text.strip().strip("'\"`")


def _is_relative_import(raw_path: str) -> bool:
    return (
        raw_path.startswith("./")
        or raw_path.startswith("../")
        or raw_path.startswith("@/")
        or raw_path.startswith("~/")
        or raw_path == "."
        or raw_path == ".."
    )


GO_CONTAINERS = {
    "source_file",
    "block",
    "if_statement",
    "for_statement",
    "function_declaration",
    "method_declaration",
}


def extract_dependencies_from_tree(
    tree: Any | None,
    code_bytes: bytes,
    language: str,
) -> list[ExtractedDependency]:
    """Extracts imported modules, packages, and relative files from source code."""
    deps: list[ExtractedDependency] = []

    if language == "Python":
        return _extract_python_ast_dependencies(code_bytes)

    if language in ("TypeScript", "TypeScript/TSX", "JavaScript", "JavaScript/JSX"):
        if tree is not None:
            _extract_js_ts_tree_dependencies(tree.root_node, code_bytes, deps)
            if deps:
                return deps
        return _extract_js_ts_dependencies(code_bytes)

    if tree is None:
        return deps

    root = tree.root_node
    if language == "Go":
        _extract_go_dependencies(root, code_bytes, deps)

    return deps


def _extract_python_ast_dependencies(code_bytes: bytes) -> list[ExtractedDependency]:
    deps: list[ExtractedDependency] = []
    try:
        code_str = code_bytes.decode("utf-8", errors="replace")
        tree = ast.parse(code_str)
    except Exception:
        return deps

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                pkg = alias.name
                deps.append(
                    ExtractedDependency(
                        raw_target=pkg,
                        dependency_type=DependencyType.IMPORT,
                        line_number=node.lineno,
                        is_relative=False,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            level_dots = "." * node.level if node.level > 0 else ""
            target = level_dots + (node.module or "")
            if target:
                is_rel = node.level > 0 or target.startswith(".")
                deps.append(
                    ExtractedDependency(
                        raw_target=target,
                        dependency_type=DependencyType.FROM_IMPORT,
                        line_number=node.lineno,
                        is_relative=is_rel,
                    )
                )

    return deps


def _extract_js_ts_tree_dependencies(
    node: Any,
    code_bytes: bytes,
    result: list[ExtractedDependency],
) -> None:
    """Extracts dependencies using Tree-Sitter AST nodes for JS/TS."""
    if node is None:
        return

    node_type = getattr(node, "type", "")
    if node_type == "import_statement":
        source_node = node.child_by_field_name("source")
        if source_node is None:
            for child in getattr(node, "children", []):
                if getattr(child, "type", "") == "string":
                    source_node = child
                    break
        if source_node:
            raw_target = _clean_str(
                code_bytes[source_node.start_byte : source_node.end_byte].decode(
                    "utf-8", errors="replace"
                )
            )
            if raw_target:
                line_no = code_bytes[:source_node.start_byte].count(b"\n") + 1
                result.append(
                    ExtractedDependency(
                        raw_target=raw_target,
                        dependency_type=DependencyType.IMPORT,
                        line_number=line_no,
                        is_relative=_is_relative_import(raw_target),
                    )
                )
    elif node_type == "export_statement":
        source_node = node.child_by_field_name("source")
        if source_node:
            raw_target = _clean_str(
                code_bytes[source_node.start_byte : source_node.end_byte].decode(
                    "utf-8", errors="replace"
                )
            )
            if raw_target:
                line_no = code_bytes[:source_node.start_byte].count(b"\n") + 1
                result.append(
                    ExtractedDependency(
                        raw_target=raw_target,
                        dependency_type=DependencyType.IMPORT,
                        line_number=line_no,
                        is_relative=_is_relative_import(raw_target),
                    )
                )
    elif node_type == "call_expression":
        fn_node = node.child_by_field_name("function")
        if fn_node:
            fn_name = (
                code_bytes[fn_node.start_byte : fn_node.end_byte]
                .decode("utf-8", errors="replace")
                .strip()
            )
            if fn_name in ("require", "import"):
                args_node = node.child_by_field_name("arguments")
                if args_node and getattr(args_node, "children", None):
                    for arg in args_node.children:
                        if getattr(arg, "type", "") == "string":
                            raw_target = _clean_str(
                                code_bytes[arg.start_byte : arg.end_byte].decode(
                                    "utf-8", errors="replace"
                                )
                            )
                            if raw_target:
                                line_no = code_bytes[:arg.start_byte].count(b"\n") + 1
                                dep_type = (
                                    DependencyType.REQUIRE
                                    if fn_name == "require"
                                    else DependencyType.IMPORT
                                )
                                result.append(
                                    ExtractedDependency(
                                        raw_target=raw_target,
                                        dependency_type=dep_type,
                                        line_number=line_no,
                                        is_relative=_is_relative_import(raw_target),
                                    )
                                )
                            break

    for child in getattr(node, "children", []):
        _extract_js_ts_tree_dependencies(child, code_bytes, result)


def _extract_js_ts_dependencies(code_bytes: bytes) -> list[ExtractedDependency]:
    result: list[ExtractedDependency] = []
    try:
        code_str = code_bytes.decode("utf-8", errors="replace")
    except Exception:
        return result

    n = len(code_str)
    i = 0
    line_no = 1

    def skip_ws_and_comments(idx: int, line: int) -> tuple[int, int]:
        while idx < n:
            c = code_str[idx]
            if c == "\n":
                line += 1
                idx += 1
            elif c.isspace():
                idx += 1
            elif c == "/" and idx + 1 < n and code_str[idx + 1] == "/":
                idx += 2
                while idx < n and code_str[idx] != "\n":
                    idx += 1
            elif c == "/" and idx + 1 < n and code_str[idx + 1] == "*":
                idx += 2
                while idx < n:
                    if code_str[idx] == "\n":
                        line += 1
                    if code_str[idx] == "*" and idx + 1 < n and code_str[idx + 1] == "/":
                        idx += 2
                        break
                    idx += 1
            else:
                break
        return idx, line

    def read_string(idx: int, line: int) -> tuple[str | None, int, int]:
        if idx >= n or code_str[idx] not in ("'", '"', "`"):
            return None, idx, line
        quote = code_str[idx]
        idx += 1
        start = idx
        while idx < n and code_str[idx] != quote:
            if code_str[idx] == "\\":
                idx += 2
                continue
            if code_str[idx] == "\n":
                line += 1
            idx += 1
        val = code_str[start:idx]
        if idx < n and code_str[idx] == quote:
            idx += 1
        return val, idx, line

    while i < n:
        i, line_no = skip_ws_and_comments(i, line_no)
        if i >= n:
            break

        c = code_str[i]

        # Ignore string literals outside imports/require
        if c in ("'", '"', "`"):
            _, i, line_no = read_string(i, line_no)
            continue

        # Check for identifier start
        is_word_start = i == 0 or not (code_str[i - 1].isalnum() or code_str[i - 1] in "_$")
        if not is_word_start:
            i += 1
            continue

        start_line = line_no

        # 1. require(...)
        if code_str.startswith("require", i) and not (
            i + 7 < n and (code_str[i + 7].isalnum() or code_str[i + 7] in "_$")
        ):
            i += 7
            i, line_no = skip_ws_and_comments(i, line_no)
            if i < n and code_str[i] == "(":
                i += 1
                i, line_no = skip_ws_and_comments(i, line_no)
                raw_target, i, line_no = read_string(i, line_no)
                if raw_target is not None:
                    raw_target = raw_target.strip()
                    if raw_target:
                        result.append(
                            ExtractedDependency(
                                raw_target=raw_target,
                                dependency_type=DependencyType.REQUIRE,
                                line_number=start_line,
                                is_relative=_is_relative_import(raw_target),
                            )
                        )
            continue

        # 2. import
        if code_str.startswith("import", i) and not (
            i + 6 < n and (code_str[i + 6].isalnum() or code_str[i + 6] in "_$")
        ):
            i += 6
            i, line_no = skip_ws_and_comments(i, line_no)
            if i >= n:
                break

            # 2a. Dynamic import: import('...')
            if code_str[i] == "(":
                i += 1
                i, line_no = skip_ws_and_comments(i, line_no)
                raw_target, i, line_no = read_string(i, line_no)
                if raw_target is not None:
                    raw_target = raw_target.strip()
                    if raw_target:
                        result.append(
                            ExtractedDependency(
                                raw_target=raw_target,
                                dependency_type=DependencyType.IMPORT,
                                line_number=start_line,
                                is_relative=_is_relative_import(raw_target),
                            )
                        )
                continue

            # 2b. Side-effect import: import '...'
            if code_str[i] in ("'", '"', "`"):
                raw_target, i, line_no = read_string(i, line_no)
                if raw_target is not None:
                    raw_target = raw_target.strip()
                    if raw_target:
                        result.append(
                            ExtractedDependency(
                                raw_target=raw_target,
                                dependency_type=DependencyType.IMPORT,
                                line_number=start_line,
                                is_relative=_is_relative_import(raw_target),
                            )
                        )
                continue

            # 2c. Static import with `from '...'` or TypeScript `import foo = require('...')`
            while i < n:
                i, line_no = skip_ws_and_comments(i, line_no)
                if i >= n or code_str[i] == ";":
                    if i < n and code_str[i] == ";":
                        i += 1
                    break

                # Check for `from`
                if (
                    code_str.startswith("from", i)
                    and not (i + 4 < n and (code_str[i + 4].isalnum() or code_str[i + 4] in "_$"))
                    and (i == 0 or not (code_str[i - 1].isalnum() or code_str[i - 1] in "_$"))
                ):
                    i += 4
                    i, line_no = skip_ws_and_comments(i, line_no)
                    raw_target, i, line_no = read_string(i, line_no)
                    if raw_target is not None:
                        raw_target = raw_target.strip()
                        if raw_target:
                            result.append(
                                ExtractedDependency(
                                    raw_target=raw_target,
                                    dependency_type=DependencyType.IMPORT,
                                    line_number=start_line,
                                    is_relative=_is_relative_import(raw_target),
                                )
                            )
                    break

                # Check for `require('...')` (e.g. `import foo = require('...')`)
                if (
                    code_str.startswith("require", i)
                    and not (i + 7 < n and (code_str[i + 7].isalnum() or code_str[i + 7] in "_$"))
                    and (i == 0 or not (code_str[i - 1].isalnum() or code_str[i - 1] in "_$"))
                ):
                    i += 7
                    i, line_no = skip_ws_and_comments(i, line_no)
                    if i < n and code_str[i] == "(":
                        i += 1
                        i, line_no = skip_ws_and_comments(i, line_no)
                        raw_target, i, line_no = read_string(i, line_no)
                        if raw_target is not None:
                            raw_target = raw_target.strip()
                            if raw_target:
                                result.append(
                                    ExtractedDependency(
                                        raw_target=raw_target,
                                        dependency_type=DependencyType.IMPORT,
                                        line_number=start_line,
                                        is_relative=_is_relative_import(raw_target),
                                    )
                                )
                    break

                # If string literal appears before `from`, skip it
                if code_str[i] in ("'", '"', "`"):
                    _, i, line_no = read_string(i, line_no)
                    continue

                i += 1
            continue

        # 3. export ... from '...'
        if code_str.startswith("export", i) and not (
            i + 6 < n and (code_str[i + 6].isalnum() or code_str[i + 6] in "_$")
        ):
            i += 6
            while i < n:
                i, line_no = skip_ws_and_comments(i, line_no)
                if i >= n or code_str[i] == ";":
                    if i < n and code_str[i] == ";":
                        i += 1
                    break

                if (
                    code_str.startswith("from", i)
                    and not (i + 4 < n and (code_str[i + 4].isalnum() or code_str[i + 4] in "_$"))
                    and (i == 0 or not (code_str[i - 1].isalnum() or code_str[i - 1] in "_$"))
                ):
                    i += 4
                    i, line_no = skip_ws_and_comments(i, line_no)
                    raw_target, i, line_no = read_string(i, line_no)
                    if raw_target is not None:
                        raw_target = raw_target.strip()
                        if raw_target:
                            result.append(
                                ExtractedDependency(
                                    raw_target=raw_target,
                                    dependency_type=DependencyType.IMPORT,
                                    line_number=start_line,
                                    is_relative=_is_relative_import(raw_target),
                                )
                            )
                    break

                if code_str[i] in ("'", '"', "`"):
                    _, i, line_no = read_string(i, line_no)
                    continue

                i += 1
            continue

        i += 1

    return result


def _extract_go_dependencies(
    node: Any,
    code_bytes: bytes,
    result: list[ExtractedDependency],
) -> None:
    for child in getattr(node, "children", []):
        if child.type == "import_declaration":
            for spec in child.children:
                if spec.type == "import_spec":
                    path_node = spec.child_by_field_name("path")
                    if path_node:
                        raw_path = _clean_str(
                            code_bytes[path_node.start_byte : path_node.end_byte].decode(
                                "utf-8", errors="replace"
                            )
                        )
                        result.append(
                            ExtractedDependency(
                                raw_target=raw_path,
                                dependency_type=DependencyType.IMPORT,
                                line_number=code_bytes[:spec.start_byte].count(b"\n") + 1,
                                is_relative=raw_path.startswith("./") or raw_path.startswith("../"),
                            )
                        )
        elif child.type in GO_CONTAINERS:
            _extract_go_dependencies(child, code_bytes, result)
