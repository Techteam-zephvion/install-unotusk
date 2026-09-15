import ast

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


JS_CONTAINERS = {
    "program",
    "statement_block",
    "export_statement",
    "export_default_statement",
    "if_statement",
    "for_statement",
    "while_statement",
    "try_statement",
    "switch_statement",
    "switch_case",
    "switch_default",
    "function_declaration",
    "function_expression",
    "arrow_function",
    "method_definition",
    "lexical_declaration",
    "variable_declaration",
    "variable_declarator",
    "expression_statement",
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

    if tree is None:
        return deps

    root = tree.root_node
    if language in ("TypeScript", "TypeScript/TSX", "JavaScript", "JavaScript/JSX"):
        _extract_js_ts_dependencies(root, code_bytes, deps)
    elif language == "Go":
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


def _extract_js_ts_dependencies(
    node: tree_sitter.Node,
    code_bytes: bytes,
    result: list[ExtractedDependency],
) -> None:
    for child in node.children:
        if child.type == "import_statement":
            source_node = child.child_by_field_name("source")
            if source_node:
                raw_path = _clean_str(
                    code_bytes[source_node.start_byte : source_node.end_byte].decode(
                        "utf-8", errors="replace"
                    )
                )
                is_rel = (
                    raw_path.startswith("./")
                    or raw_path.startswith("../")
                    or raw_path.startswith("@/")
                )
                result.append(
                    ExtractedDependency(
                        raw_target=raw_path,
                        dependency_type=DependencyType.IMPORT,
                        line_number=child.start_point.row + 1,
                        is_relative=is_rel,
                    )
                )

        elif child.type == "call_expression":
            fn_node = child.child_by_field_name("function")
            if fn_node:
                fn_text = code_bytes[fn_node.start_byte : fn_node.end_byte].decode(
                    "utf-8", errors="replace"
                )
                if fn_text == "require":
                    args_node = child.child_by_field_name("arguments")
                    if args_node:
                        for arg in args_node.children:
                            if arg.type in ("string", "string_fragment", "template_string"):
                                raw_arg = _clean_str(
                                    code_bytes[arg.start_byte : arg.end_byte].decode(
                                        "utf-8", errors="replace"
                                    )
                                )
                                is_rel = (
                                    raw_arg.startswith("./")
                                    or raw_arg.startswith("../")
                                    or raw_arg.startswith("@/")
                                )
                                result.append(
                                    ExtractedDependency(
                                        raw_target=raw_arg,
                                        dependency_type=DependencyType.REQUIRE,
                                        line_number=child.start_point.row + 1,
                                        is_relative=is_rel,
                                    )
                                )
        if child.type in JS_CONTAINERS:
            _extract_js_ts_dependencies(child, code_bytes, result)


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
                                line_number=spec.start_point.row + 1,
                                is_relative=raw_path.startswith("./") or raw_path.startswith("../"),
                            )
                        )
        elif child.type in GO_CONTAINERS:
            _extract_go_dependencies(child, code_bytes, result)
