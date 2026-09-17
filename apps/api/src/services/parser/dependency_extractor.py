import ast
import re

import tree_sitter

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


JS_IMPORT_RE = re.compile(
    r"""(?:^|[;\n])\s*(?:export\s+(?:[\w\s{},*]+from\s+)?|import\s+(?:(?:type\s+)?[\w\s{},*]+from\s+)?|import\s+)['"]([^'"]+)['"]""",
    re.MULTILINE,
)
JS_REQUIRE_RE = re.compile(r"""(?:require|import)\s*\(\s*['"]([^'"]+)['"]\s*\)""")

JS_CONTAINERS = {
    "program",
    "export_statement",
    "export_default_statement",
}

GO_CONTAINERS = {
    "source_file",
    "block",
    "if_statement",
    "for_statement",
    "function_declaration",
    "method_declaration",
}


def extract_dependencies_from_tree(
    tree: tree_sitter.Tree | None,
    code_bytes: bytes,
    language: str,
) -> list[ExtractedDependency]:
    """Extracts imported modules, packages, and relative files from source code."""
    deps: list[ExtractedDependency] = []

    if language == "Python":
        return _extract_python_ast_dependencies(code_bytes)

    if language in ("TypeScript", "TypeScript/TSX", "JavaScript", "JavaScript/JSX"):
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
                pkg = alias.name.split(".")[0]
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


def _extract_js_ts_dependencies(code_bytes: bytes) -> list[ExtractedDependency]:
    result: list[ExtractedDependency] = []
    try:
        code_str = code_bytes.decode("utf-8", errors="replace")
    except Exception:
        return result

    for match in JS_IMPORT_RE.finditer(code_str):
        raw_path = match.group(1).strip()
        if not raw_path:
            continue
        line_no = code_str.count("\n", 0, match.start()) + 1
        is_rel = (
            raw_path.startswith("./")
            or raw_path.startswith("../")
            or raw_path.startswith("@/")
        )
        result.append(
            ExtractedDependency(
                raw_target=raw_path,
                dependency_type=DependencyType.IMPORT,
                line_number=line_no,
                is_relative=is_rel,
            )
        )

    for match in JS_REQUIRE_RE.finditer(code_str):
        raw_path = match.group(1).strip()
        if not raw_path:
            continue
        line_no = code_str.count("\n", 0, match.start()) + 1
        is_rel = (
            raw_path.startswith("./")
            or raw_path.startswith("../")
            or raw_path.startswith("@/")
        )
        result.append(
            ExtractedDependency(
                raw_target=raw_path,
                dependency_type=DependencyType.REQUIRE,
                line_number=line_no,
                is_relative=is_rel,
            )
        )

    return result


def _extract_go_dependencies(
    node: tree_sitter.Node,
    code_bytes: bytes,
    result: list[ExtractedDependency],
) -> None:
    for child in node.children:
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
