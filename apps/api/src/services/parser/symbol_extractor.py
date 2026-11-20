from __future__ import annotations

import ast
from typing import Any

try:
    import tree_sitter
except ImportError:
    tree_sitter = None  # type: ignore[assignment]

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
        children: list[ExtractedSymbol] | None = None,
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
    """Extracts structural symbols from source code via native Tree-Sitter or Universal Fallback."""
    symbols: list[ExtractedSymbol] = []

    if language == "Python":
        symbols = _extract_python_ast_symbols(code_bytes)
    elif tree is not None:
        root = tree.root_node
        if language in ("TypeScript", "TypeScript/TSX", "JavaScript", "JavaScript/JSX"):
            _extract_js_ts_symbols(root, code_bytes, "", symbols)
        elif language == "Go":
            _extract_go_symbols(root, code_bytes, "", symbols)
        elif language == "Java":
            _extract_java_symbols(root, code_bytes, "", symbols)
        elif language == "Rust":
            _extract_rust_symbols(root, code_bytes, "", symbols)
        elif language in ("C++", "C++ Header", "C", "C/C++ Header"):
            _extract_cpp_c_symbols(root, code_bytes, "", symbols)
        elif language == "C#":
            _extract_csharp_symbols(root, code_bytes, "", symbols)
        elif language == "Dart":
            _extract_dart_symbols(root, code_bytes, "", symbols)

    # Phase B: Universal Regex & Brace/Indentation Chunker Fallback
    # Active for Dart, Rust, Java, Kotlin, Swift, C++, PHP, Ruby, etc., or when AST has 0 symbols
    if not symbols:
        from apps.api.src.services.parser.universal_parser import extract_universal_symbols

        symbols = extract_universal_symbols(code_bytes, language)

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
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    class_sym.children.append(
                        ExtractedSymbol(
                            name=item.name,
                            symbol_type=SymbolType.METHOD,
                            qualified_name=f"{node.name}.{item.name}",
                            start_line=item.lineno,
                            end_line=getattr(item, "end_lineno", item.lineno),
                        )
                    )
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
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


def _extract_java_symbols(
    node: Any,
    code_bytes: bytes,
    parent_scope: str,
    result: list[ExtractedSymbol],
) -> None:
    for child in getattr(node, "children", []):
        c_type = getattr(child, "type", "")
        if c_type in ("class_declaration", "interface_declaration", "record_declaration", "enum_declaration"):
            name_node = child.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qual = f"{parent_scope}.{name}" if parent_scope else name
                st, et = _get_node_lines(child, code_bytes)
                sym_type = SymbolType.CLASS if c_type == "class_declaration" else SymbolType.TYPE
                cls_sym = ExtractedSymbol(
                    name=name,
                    symbol_type=sym_type,
                    qualified_name=qual,
                    start_line=st,
                    end_line=et,
                )
                result.append(cls_sym)
                body = child.child_by_field_name("body")
                if body:
                    _extract_java_symbols(body, code_bytes, qual, result)
        elif c_type in ("method_declaration", "constructor_declaration"):
            name_node = child.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qual = f"{parent_scope}.{name}" if parent_scope else name
                st, et = _get_node_lines(child, code_bytes)
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.METHOD,
                        qualified_name=qual,
                        start_line=st,
                        end_line=et,
                    )
                )
        elif c_type in ("program", "class_body", "interface_body"):
            _extract_java_symbols(child, code_bytes, parent_scope, result)


def _extract_rust_symbols(
    node: Any,
    code_bytes: bytes,
    parent_scope: str,
    result: list[ExtractedSymbol],
) -> None:
    for child in getattr(node, "children", []):
        c_type = getattr(child, "type", "")
        if c_type in ("struct_item", "enum_item", "trait_item", "union_item"):
            name_node = child.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qual = f"{parent_scope}::{name}" if parent_scope else name
                st, et = _get_node_lines(child, code_bytes)
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.TYPE,
                        qualified_name=qual,
                        start_line=st,
                        end_line=et,
                    )
                )
        elif c_type == "function_item":
            name_node = child.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qual = f"{parent_scope}::{name}" if parent_scope else name
                st, et = _get_node_lines(child, code_bytes)
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.FUNCTION if not parent_scope else SymbolType.METHOD,
                        qualified_name=qual,
                        start_line=st,
                        end_line=et,
                    )
                )
        elif c_type == "impl_item":
            type_node = child.child_by_field_name("type")
            scope_name = _get_node_text(type_node, code_bytes) if type_node else parent_scope
            body = child.child_by_field_name("body")
            if body:
                _extract_rust_symbols(body, code_bytes, scope_name, result)
        elif c_type in ("source_file", "declaration_list"):
            _extract_rust_symbols(child, code_bytes, parent_scope, result)


def _extract_cpp_c_symbols(
    node: Any,
    code_bytes: bytes,
    parent_scope: str,
    result: list[ExtractedSymbol],
) -> None:
    for child in getattr(node, "children", []):
        c_type = getattr(child, "type", "")
        if c_type in ("class_specifier", "struct_specifier", "enum_specifier"):
            name_node = child.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qual = f"{parent_scope}::{name}" if parent_scope else name
                st, et = _get_node_lines(child, code_bytes)
                sym_type = SymbolType.CLASS if c_type == "class_specifier" else SymbolType.TYPE
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=sym_type,
                        qualified_name=qual,
                        start_line=st,
                        end_line=et,
                    )
                )
                body = child.child_by_field_name("body")
                if body:
                    _extract_cpp_c_symbols(body, code_bytes, qual, result)
        elif c_type == "function_definition":
            decl = child.child_by_field_name("declarator")
            # Navigate nested declarators to find identifier
            while decl and getattr(decl, "child_by_field_name", None) and decl.child_by_field_name("declarator"):
                decl = decl.child_by_field_name("declarator")
            if decl:
                name = _get_node_text(decl, code_bytes).split("(")[0].strip()
                if name:
                    qual = f"{parent_scope}::{name}" if parent_scope else name
                    st, et = _get_node_lines(child, code_bytes)
                    result.append(
                        ExtractedSymbol(
                            name=name,
                            symbol_type=SymbolType.FUNCTION if not parent_scope else SymbolType.METHOD,
                            qualified_name=qual,
                            start_line=st,
                            end_line=et,
                        )
                    )
        elif c_type in ("translation_unit", "field_declaration_list"):
            _extract_cpp_c_symbols(child, code_bytes, parent_scope, result)


def _extract_csharp_symbols(
    node: Any,
    code_bytes: bytes,
    parent_scope: str,
    result: list[ExtractedSymbol],
) -> None:
    for child in getattr(node, "children", []):
        c_type = getattr(child, "type", "")
        if c_type in ("class_declaration", "interface_declaration", "struct_declaration", "enum_declaration", "record_declaration"):
            name_node = child.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qual = f"{parent_scope}.{name}" if parent_scope else name
                st, et = _get_node_lines(child, code_bytes)
                sym_type = SymbolType.CLASS if c_type in ("class_declaration", "record_declaration") else SymbolType.TYPE
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=sym_type,
                        qualified_name=qual,
                        start_line=st,
                        end_line=et,
                    )
                )
                body = child.child_by_field_name("body")
                if body:
                    _extract_csharp_symbols(body, code_bytes, qual, result)
        elif c_type in ("method_declaration", "constructor_declaration"):
            name_node = child.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qual = f"{parent_scope}.{name}" if parent_scope else name
                st, et = _get_node_lines(child, code_bytes)
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.METHOD,
                        qualified_name=qual,
                        start_line=st,
                        end_line=et,
                    )
                )
        elif c_type in ("compilation_unit", "declaration_list", "namespace_declaration"):
            _extract_csharp_symbols(child, code_bytes, parent_scope, result)


def _extract_dart_symbols(
    node: Any,
    code_bytes: bytes,
    parent_scope: str,
    result: list[ExtractedSymbol],
) -> None:
    for child in getattr(node, "children", []):
        c_type = getattr(child, "type", "")
        if c_type in ("class_definition", "enum_declaration", "mixin_declaration", "extension_declaration"):
            name_node = child.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qual = f"{parent_scope}.{name}" if parent_scope else name
                st, et = _get_node_lines(child, code_bytes)
                sym_type = SymbolType.CLASS if c_type == "class_definition" else SymbolType.TYPE
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=sym_type,
                        qualified_name=qual,
                        start_line=st,
                        end_line=et,
                    )
                )
                body = child.child_by_field_name("body")
                if body:
                    _extract_dart_symbols(body, code_bytes, qual, result)
        elif c_type in ("method_signature", "function_signature", "function_declaration"):
            name_node = child.child_by_field_name("name")
            if name_node:
                name = _get_node_text(name_node, code_bytes)
                qual = f"{parent_scope}.{name}" if parent_scope else name
                st, et = _get_node_lines(child, code_bytes)
                result.append(
                    ExtractedSymbol(
                        name=name,
                        symbol_type=SymbolType.FUNCTION if not parent_scope else SymbolType.METHOD,
                        qualified_name=qual,
                        start_line=st,
                        end_line=et,
                    )
                )
        elif c_type in ("program", "class_body"):
            _extract_dart_symbols(child, code_bytes, parent_scope, result)

