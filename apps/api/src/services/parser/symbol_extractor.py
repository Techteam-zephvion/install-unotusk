import ast
from typing import Any

import tree_sitter

from apps.api.src.models.enums import SymbolType


class ExtractedSymbol:
    def __init__(
        self,
        name: str,
        symbol_type: SymbolType,
        qualified_name: str,
        start_line: int,
        end_line: int,
        metadata: dict[str, Any] | None = None,
        children: list["ExtractedSymbol"] | None = None,
    ):
        self.name = name
        self.symbol_type = symbol_type
        self.qualified_name = qualified_name
        self.start_line = start_line
        self.end_line = end_line
        self.metadata = metadata or {}
        self.children = children or []


def _get_node_text(node: tree_sitter.Node, code_bytes: bytes) -> str:
    return code_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _get_node_lines(node: tree_sitter.Node, code_bytes: bytes) -> tuple[int, int]:
    """Safely compute (start_line, end_line) from byte offsets without triggering
    Cython Point descriptor memory bugs in Python 3.12."""
    try:
        sb = node.start_byte
        eb = node.end_byte
        start_line = code_bytes[:sb].count(b"\n") + 1
        end_line = start_line + code_bytes[sb:eb].count(b"\n")
        return start_line, max(start_line, end_line)
    except Exception:
        return 1, 1


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
    "type_declaration",
}


def extract_symbols_from_tree(
    tree: tree_sitter.Tree | None,
    code_bytes: bytes,
    language: str,
) -> list[ExtractedSymbol]:
    """Extracts structural symbols from source code."""
    symbols: list[ExtractedSymbol] = []

    if language == "Python":
        return _extract_python_ast_symbols(code_bytes)

    if tree is None:
        return symbols

    root = tree.root_node
    if language in ("TypeScript", "TypeScript/TSX", "JavaScript", "JavaScript/JSX"):
        _extract_js_ts_symbols(root, code_bytes, "", symbols)
    elif language == "Go":
        _extract_go_symbols(root, code_bytes, "", symbols)

    return symbols


def _extract_python_ast_symbols(code_bytes: bytes) -> list[ExtractedSymbol]:
    symbols: list[ExtractedSymbol] = []
    try:
        code_str = code_bytes.decode("utf-8", errors="replace")
        tree = ast.parse(code_str)
    except Exception:
        return symbols

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_sym = ExtractedSymbol(
                name=node.name,
                symbol_type=SymbolType.CLASS,
                qualified_name=node.name,
                start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
            )
            symbols.append(class_sym)
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    class_sym.children.append(
                        ExtractedSymbol(
                            name=item.name,
                            symbol_type=SymbolType.METHOD,
                            qualified_name=f"{node.name}.{item.name}",
                            start_line=item.lineno,
                            end_line=getattr(item, "end_lineno", item.lineno),
                        )
                    )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(
                ExtractedSymbol(
                    name=node.name,
                    symbol_type=SymbolType.FUNCTION,
                    qualified_name=node.name,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                )
            )

    return symbols


def _extract_js_ts_symbols(
    node: tree_sitter.Node,
    code_bytes: bytes,
    parent_scope: str,
    result: list[ExtractedSymbol],
) -> None:
    for child in node.children:
        curr = child
        if curr.type in ("export_statement", "export_default_statement"):
            decl = curr.child_by_field_name("declaration") or curr.child_by_field_name("value")
            if not decl:
                named = curr.named_children
                if named:
                    decl = named[0]
            if decl:
                curr = decl

        if curr.type == "class_declaration":
            name_node = curr.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qualified_name = f"{parent_scope}.{name}" if parent_scope else name
                start_line, end_line = _get_node_lines(curr, code_bytes)
                sym = ExtractedSymbol(
                    name=name,
                    symbol_type=SymbolType.CLASS,
                    qualified_name=qualified_name,
                    start_line=start_line,
                    end_line=end_line,
                )
                result.append(sym)
                body_node = curr.child_by_field_name("body")
                if body_node:
                    _extract_js_ts_symbols(body_node, code_bytes, qualified_name, sym.children)

        elif curr.type == "function_declaration":
            name_node = curr.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qualified_name = f"{parent_scope}.{name}" if parent_scope else name
                start_line, end_line = _get_node_lines(curr, code_bytes)
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.FUNCTION,
                        qualified_name=qualified_name,
                        start_line=start_line,
                        end_line=end_line,
                    )
                )

        elif curr.type == "method_definition":
            name_node = curr.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qualified_name = f"{parent_scope}.{name}" if parent_scope else name
                start_line, end_line = _get_node_lines(curr, code_bytes)
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.METHOD,
                        qualified_name=qualified_name,
                        start_line=start_line,
                        end_line=end_line,
                    )
                )

        elif curr.type == "interface_declaration":
            name_node = curr.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qualified_name = f"{parent_scope}.{name}" if parent_scope else name
                start_line, end_line = _get_node_lines(curr, code_bytes)
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.INTERFACE,
                        qualified_name=qualified_name,
                        start_line=start_line,
                        end_line=end_line,
                    )
                )

        elif curr.type == "type_alias_declaration":
            name_node = curr.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qualified_name = f"{parent_scope}.{name}" if parent_scope else name
                start_line, end_line = _get_node_lines(curr, code_bytes)
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.TYPE,
                        qualified_name=qualified_name,
                        start_line=start_line,
                        end_line=end_line,
                    )
                )

        elif curr.type == "enum_declaration":
            name_node = curr.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qualified_name = f"{parent_scope}.{name}" if parent_scope else name
                start_line, end_line = _get_node_lines(curr, code_bytes)
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.ENUM,
                        qualified_name=qualified_name,
                        start_line=start_line,
                        end_line=end_line,
                    )
                )
        elif curr.type in JS_CONTAINERS:
            _extract_js_ts_symbols(curr, code_bytes, parent_scope, result)


def _extract_go_symbols(
    node: tree_sitter.Node,
    code_bytes: bytes,
    parent_scope: str,
    result: list[ExtractedSymbol],
) -> None:
    for child in node.children:
        if child.type == "function_declaration":
            name_node = child.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                start_line, end_line = _get_node_lines(child, code_bytes)
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.FUNCTION,
                        qualified_name=name,
                        start_line=start_line,
                        end_line=end_line,
                    )
                )
        elif child.type == "method_declaration":
            name_node = child.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                start_line, end_line = _get_node_lines(child, code_bytes)
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.METHOD,
                        qualified_name=name,
                        start_line=start_line,
                        end_line=end_line,
                    )
                )
        elif child.type == "type_declaration":
            for spec in child.children:
                if spec.type == "type_spec":
                    name_node = spec.child_by_field_name("name")
                    if name_node:
                        name = _get_node_text(name_node, code_bytes)
                        start_line, end_line = _get_node_lines(spec, code_bytes)
                        result.append(
                            ExtractedSymbol(
                                name=name,
                                symbol_type=SymbolType.TYPE,
                                qualified_name=name,
                                start_line=start_line,
                                end_line=end_line,
                            )
                        )
        elif child.type in GO_CONTAINERS:
            _extract_go_symbols(child, code_bytes, parent_scope, result)
