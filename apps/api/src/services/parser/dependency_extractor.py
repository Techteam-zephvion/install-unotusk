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


def extract_dependencies_from_tree(
    tree: tree_sitter.Tree,
    code_bytes: bytes,
    language: str,
) -> list[ExtractedDependency]:
    """Extracts imported modules, packages, and relative files from Tree-sitter AST."""
    deps: list[ExtractedDependency] = []
    root = tree.root_node

    if language == "Python":
        _extract_python_dependencies(root, code_bytes, deps)
    elif language in ("TypeScript", "TypeScript/TSX", "JavaScript", "JavaScript/JSX"):
        _extract_js_ts_dependencies(root, code_bytes, deps)
    elif language == "Go":
        _extract_go_dependencies(root, code_bytes, deps)

    return deps


def _extract_python_dependencies(
    node: tree_sitter.Node,
    code_bytes: bytes,
    result: list[ExtractedDependency],
) -> None:
    for child in node.children:
        if child.type == "import_statement":
            # e.g., import os, sys
            # Parse names
            for name_node in child.children:
                if name_node.type == "dotted_name":
                    pkg = code_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace")
                    result.append(
                        ExtractedDependency(
                            raw_target=pkg.split(".")[0],
                            dependency_type=DependencyType.IMPORT,
                            line_number=child.start_point.row + 1,
                            is_relative=False,
                        )
                    )

        elif child.type == "import_from_statement":
            # e.g., from .utils import foo or from fastapi import Depends
            module_name_node = child.child_by_field_name("module_name")
            if module_name_node:
                raw_mod = code_bytes[module_name_node.start_byte:module_name_node.end_byte].decode("utf-8", errors="replace")
                is_rel = raw_mod.startswith(".")
                result.append(
                    ExtractedDependency(
                        raw_target=raw_mod,
                        dependency_type=DependencyType.FROM_IMPORT,
                        line_number=child.start_point.row + 1,
                        is_relative=is_rel,
                    )
                )
        else:
            _extract_python_dependencies(child, code_bytes, result)


def _extract_js_ts_dependencies(
    node: tree_sitter.Node,
    code_bytes: bytes,
    result: list[ExtractedDependency],
) -> None:
    for child in node.children:
        if child.type == "import_statement":
            source_node = child.child_by_field_name("source")
            if source_node:
                raw_path = _clean_str(code_bytes[source_node.start_byte:source_node.end_byte].decode("utf-8", errors="replace"))
                is_rel = raw_path.startswith("./") or raw_path.startswith("../") or raw_path.startswith("@/")
                result.append(
                    ExtractedDependency(
                        raw_target=raw_path,
                        dependency_type=DependencyType.IMPORT,
                        line_number=child.start_point.row + 1,
                        is_relative=is_rel,
                    )
                )

        elif child.type == "call_expression":
            # Check for require('...')
            fn_node = child.child_by_field_name("function")
            if fn_node:
                fn_text = code_bytes[fn_node.start_byte:fn_node.end_byte].decode("utf-8", errors="replace")
                if fn_text == "require":
                    args_node = child.child_by_field_name("arguments")
                    if args_node and len(args_node.children) >= 2:
                        raw_arg = _clean_str(code_bytes[args_node.children[1].start_byte:args_node.children[1].end_byte].decode("utf-8", errors="replace"))
                        is_rel = raw_arg.startswith("./") or raw_arg.startswith("../") or raw_arg.startswith("@/")
                        result.append(
                            ExtractedDependency(
                                raw_target=raw_arg,
                                dependency_type=DependencyType.REQUIRE,
                                line_number=child.start_point.row + 1,
                                is_relative=is_rel,
                            )
                        )
        else:
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
                        raw_path = _clean_str(code_bytes[path_node.start_byte:path_node.end_byte].decode("utf-8", errors="replace"))
                        result.append(
                            ExtractedDependency(
                                raw_target=raw_path,
                                dependency_type=DependencyType.IMPORT,
                                line_number=spec.start_point.row + 1,
                                is_relative=raw_path.startswith("./") or raw_path.startswith("../"),
                            )
                        )
        else:
            _extract_go_dependencies(child, code_bytes, result)
