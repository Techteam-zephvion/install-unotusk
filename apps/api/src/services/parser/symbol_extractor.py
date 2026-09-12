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
    return code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def extract_symbols_from_tree(
    tree: tree_sitter.Tree,
    code_bytes: bytes,
    language: str,
) -> list[ExtractedSymbol]:
    """Recursively extracts structural symbols from Tree-sitter AST."""
    symbols: list[ExtractedSymbol] = []
    root = tree.root_node

    if language == "Python":
        _extract_python_symbols(root, code_bytes, "", symbols)
    elif language in ("TypeScript", "TypeScript/TSX", "JavaScript", "JavaScript/JSX"):
        _extract_js_ts_symbols(root, code_bytes, "", symbols)
    elif language == "Go":
        _extract_go_symbols(root, code_bytes, "", symbols)

    return symbols


def _extract_python_symbols(
    node: tree_sitter.Node,
    code_bytes: bytes,
    parent_scope: str,
    result: list[ExtractedSymbol],
) -> None:
    for child in node.children:
        if child.type == "class_definition":
            name_node = child.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qualified_name = f"{parent_scope}.{name}" if parent_scope else name
                sym = ExtractedSymbol(
                    name=name,
                    symbol_type=SymbolType.CLASS,
                    qualified_name=qualified_name,
                    start_line=child.start_point.row + 1,
                    end_line=child.end_point.row + 1,
                )
                result.append(sym)
                # Recurse inside class body for methods
                body_node = child.child_by_field_name("body")
                if body_node:
                    _extract_python_symbols(body_node, code_bytes, qualified_name, sym.children)

        elif child.type == "function_definition":
            name_node = child.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qualified_name = f"{parent_scope}.{name}" if parent_scope else name
                sym_type = SymbolType.METHOD if parent_scope else SymbolType.FUNCTION
                sym = ExtractedSymbol(
                    name=name,
                    symbol_type=sym_type,
                    qualified_name=qualified_name,
                    start_line=child.start_point.row + 1,
                    end_line=child.end_point.row + 1,
                )
                result.append(sym)
        else:
            _extract_python_symbols(child, code_bytes, parent_scope, result)


def _extract_js_ts_symbols(
    node: tree_sitter.Node,
    code_bytes: bytes,
    parent_scope: str,
    result: list[ExtractedSymbol],
) -> None:
    for child in node.children:
        # Unwrap export statements
        curr = child
        if curr.type in ("export_statement", "export_default_statement"):
            for sub in curr.children:
                if sub.type not in ("export", "default"):
                    curr = sub
                    break

        if curr.type == "class_declaration":
            name_node = curr.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qualified_name = f"{parent_scope}.{name}" if parent_scope else name
                sym = ExtractedSymbol(
                    name=name,
                    symbol_type=SymbolType.CLASS,
                    qualified_name=qualified_name,
                    start_line=curr.start_point.row + 1,
                    end_line=curr.end_point.row + 1,
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
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.FUNCTION,
                        qualified_name=qualified_name,
                        start_line=curr.start_point.row + 1,
                        end_line=curr.end_point.row + 1,
                    )
                )

        elif curr.type == "method_definition":
            name_node = curr.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qualified_name = f"{parent_scope}.{name}" if parent_scope else name
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.METHOD,
                        qualified_name=qualified_name,
                        start_line=curr.start_point.row + 1,
                        end_line=curr.end_point.row + 1,
                    )
                )

        elif curr.type == "interface_declaration":
            name_node = curr.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qualified_name = f"{parent_scope}.{name}" if parent_scope else name
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.INTERFACE,
                        qualified_name=qualified_name,
                        start_line=curr.start_point.row + 1,
                        end_line=curr.end_point.row + 1,
                    )
                )

        elif curr.type == "type_alias_declaration":
            name_node = curr.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qualified_name = f"{parent_scope}.{name}" if parent_scope else name
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.TYPE,
                        qualified_name=qualified_name,
                        start_line=curr.start_point.row + 1,
                        end_line=curr.end_point.row + 1,
                    )
                )

        elif curr.type == "enum_declaration":
            name_node = curr.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qualified_name = f"{parent_scope}.{name}" if parent_scope else name
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.ENUM,
                        qualified_name=qualified_name,
                        start_line=curr.start_point.row + 1,
                        end_line=curr.end_point.row + 1,
                    )
                )
        else:
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
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.FUNCTION,
                        qualified_name=name,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                    )
                )
        elif child.type == "method_declaration":
            name_node = child.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.METHOD,
                        qualified_name=name,
                        start_line=child.start_point.row + 1,
                        end_line=child.end_point.row + 1,
                    )
                )
        elif child.type == "type_declaration":
            for spec in child.children:
                if spec.type == "type_spec":
                    name_node = spec.child_by_field_name("name")
                    if name_node:
                        name = _get_node_text(name_node, code_bytes)
                        result.append(
                            ExtractedSymbol(
                                name=name,
                                symbol_type=SymbolType.TYPE,
                                qualified_name=name,
                                start_line=spec.start_point.row + 1,
                                end_line=spec.end_point.row + 1,
                            )
                        )
        else:
            _extract_go_symbols(child, code_bytes, parent_scope, result)
