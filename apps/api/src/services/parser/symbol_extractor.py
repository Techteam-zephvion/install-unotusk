from __future__ import annotations

import ast
import bisect
import re
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
    """Extracts structural symbols from source code with dual-tier fallback."""
    symbols: list[ExtractedSymbol] = []

    if language == "Python":
        py_symbols = _extract_python_ast_symbols(code_bytes)
        if py_symbols:
            return py_symbols
        return extract_universal_symbols(code_bytes, language)

    if tree is not None:
        root = getattr(tree, "root_node", None)
        if root is not None:
            if language in ("TypeScript", "TypeScript/TSX", "JavaScript", "JavaScript/JSX"):
                _extract_js_ts_symbols(root, code_bytes, "", symbols)
                if symbols:
                    return symbols
            elif language == "Go":
                _extract_go_symbols(root, code_bytes, "", symbols)
                if symbols:
                    return symbols

    # Tier-2 Universal Structural Heuristics Fallback (Dart, Java, Kotlin, Rust, C#, C++, PHP, Swift, SQL, Shell, etc.)
    return extract_universal_symbols(code_bytes, language)


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


# ---------------------------------------------------------------------------
# Tier-2 Universal Structural Heuristic Symbol Extractor
# ---------------------------------------------------------------------------

def mask_comments_and_strings(code_str: str, language: str) -> str:
    """
    Mask comments and string literals with spaces while preserving exact character length
    and line structure (newlines are strictly preserved).
    """
    n = len(code_str)
    chars = list(code_str)
    i = 0
    is_hash_comment_lang = language in ("Python", "Shell", "Ruby", "YAML", "TOML")
    is_sql = language == "SQL"

    while i < n:
        c = code_str[i]

        # 1. Double or Triple Quoted Strings
        if c == '"':
            if i + 2 < n and code_str[i : i + 3] == '"""':
                chars[i] = " "
                chars[i + 1] = " "
                chars[i + 2] = " "
                i += 3
                while i < n:
                    if code_str[i : i + 3] == '"""':
                        chars[i] = " "
                        chars[i + 1] = " "
                        chars[i + 2] = " "
                        i += 3
                        break
                    if chars[i] != "\n":
                        chars[i] = " "
                    i += 1
                continue
            else:
                chars[i] = " "
                i += 1
                while i < n:
                    if code_str[i] == "\\" and i + 1 < n:
                        chars[i] = " "
                        if chars[i + 1] != "\n":
                            chars[i + 1] = " "
                        i += 2
                        continue
                    if code_str[i] == '"':
                        chars[i] = " "
                        i += 1
                        break
                    if chars[i] != "\n":
                        chars[i] = " "
                    i += 1
                continue

        # 2. Single or Triple Single-Quoted Strings
        if c == "'":
            if i + 2 < n and code_str[i : i + 3] == "'''":
                chars[i] = " "
                chars[i + 1] = " "
                chars[i + 2] = " "
                i += 3
                while i < n:
                    if code_str[i : i + 3] == "'''":
                        chars[i] = " "
                        chars[i + 1] = " "
                        chars[i + 2] = " "
                        i += 3
                        break
                    if chars[i] != "\n":
                        chars[i] = " "
                    i += 1
                continue
            else:
                chars[i] = " "
                i += 1
                while i < n:
                    if code_str[i] == "\\" and i + 1 < n:
                        chars[i] = " "
                        if chars[i + 1] != "\n":
                            chars[i + 1] = " "
                        i += 2
                        continue
                    if code_str[i] == "'":
                        chars[i] = " "
                        i += 1
                        break
                    if chars[i] != "\n":
                        chars[i] = " "
                    i += 1
                continue

        # 3. Backtick Strings (JS/TS/Go/Shell)
        if c == "`":
            chars[i] = " "
            i += 1
            while i < n:
                if code_str[i] == "`":
                    chars[i] = " "
                    i += 1
                    break
                if chars[i] != "\n":
                    chars[i] = " "
                i += 1
            continue

        # 4. Single-line comment //
        if c == "/" and i + 1 < n and code_str[i + 1] == "/":
            chars[i] = " "
            chars[i + 1] = " "
            i += 2
            while i < n and code_str[i] != "\n":
                chars[i] = " "
                i += 1
            continue

        # 5. Multi-line comment /* ... */
        if c == "/" and i + 1 < n and code_str[i + 1] == "*":
            chars[i] = " "
            chars[i + 1] = " "
            i += 2
            while i < n:
                if code_str[i : i + 2] == "*/":
                    chars[i] = " "
                    chars[i + 1] = " "
                    i += 2
                    break
                if chars[i] != "\n":
                    chars[i] = " "
                i += 1
            continue

        # 6. Hash comments (#) for Python/Shell/Ruby/YAML
        if c == "#" and is_hash_comment_lang:
            chars[i] = " "
            i += 1
            while i < n and code_str[i] != "\n":
                chars[i] = " "
                i += 1
            continue

        # 7. SQL comments (-- ...)
        if c == "-" and i + 1 < n and code_str[i + 1] == "-" and is_sql:
            chars[i] = " "
            chars[i + 1] = " "
            i += 2
            while i < n and code_str[i] != "\n":
                chars[i] = " "
                i += 1
            continue

        i += 1

    return "".join(chars)


CONTROL_FLOW_KEYWORDS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "try",
    "else",
    "do",
    "finally",
    "with",
    "lock",
    "synchronized",
    "case",
    "default",
    "return",
    "throw",
    "yield",
    "where",
    "select",
    "from",
    "let",
    "const",
    "var",
    "final",
}

CONTAINER_KEYWORD_MAP = {
    "class": SymbolType.CLASS,
    "interface": SymbolType.INTERFACE,
    "struct": SymbolType.TYPE,
    "enum": SymbolType.ENUM,
    "trait": SymbolType.INTERFACE,
    "impl": SymbolType.CLASS,
    "record": SymbolType.CLASS,
    "mixin": SymbolType.CLASS,
    "extension": SymbolType.MODULE,
}

RE_CONTAINER = re.compile(
    r"\b(class|interface|struct|enum|trait|impl|record|mixin|extension)\s+([A-Za-z0-9_]+)"
)

RE_RUST_IMPL = re.compile(
    r"\bimpl(?:\s+[A-Za-z0-9_<>]+)?(?:\s+for)?\s+([A-Za-z0-9_]+)"
)

RE_DART_ARROW = re.compile(
    r"(?:^|[\s;{}])([A-Za-z0-9_<>\[\],\?*&]+(?:\s+[A-Za-z0-9_<>\[\],\?*&]+)*)\s+([A-Za-z0-9_]+)\s*\(([^;{}]*)\)\s*=>"
)

RE_SQL_STMT = re.compile(
    r"(?i)\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:TEMP(?:ORARY)?\s+)?(TABLE|VIEW|PROCEDURE|FUNCTION|TRIGGER|INDEX)\s+(?:IF\s+NOT\s+EXISTS\s+)?([`\"'\[]?[a-zA-Z0-9_.]*[`\"'\]]?)"
)

RE_SHELL_FUNC = re.compile(
    r"(?:^|[\n;])\s*(?:function\s+([a-zA-Z0-9_-]+)(?:\s*\(\s*\))?|([a-zA-Z0-9_-]+)\s*\(\s*\))\s*\{"
)


def extract_universal_symbols(code_bytes: bytes, language: str) -> list[ExtractedSymbol]:
    """
    Tier-2 Universal Structural Symbol Extractor.
    Extracts classes, interfaces, enums, structs, functions, and methods
    with accurate line ranges and scope hierarchies across all languages.
    """
    symbols: list[ExtractedSymbol] = []
    try:
        code_str = code_bytes.decode("utf-8", errors="replace")
    except Exception:
        return symbols

    if not code_str.strip():
        return symbols

    # Pre-compute newline offsets for fast index-to-line translation
    line_offsets = [0]
    for idx, char in enumerate(code_str):
        if char == "\n":
            line_offsets.append(idx + 1)

    def get_line_num(byte_or_char_idx: int) -> int:
        return bisect.bisect_right(line_offsets, byte_or_char_idx)

    # Special handler for SQL
    if language == "SQL":
        for match in RE_SQL_STMT.finditer(code_str):
            stmt_type = match.group(1).upper()
            raw_name = match.group(2).strip("`\"'[]")
            start_idx = match.start()
            start_line = get_line_num(start_idx)
            end_match = re.search(r";|\bGO\b", code_str[start_idx:], re.IGNORECASE)
            if end_match:
                end_line = get_line_num(start_idx + end_match.end())
            else:
                end_line = start_line + 5

            sym_type = (
                SymbolType.FUNCTION
                if stmt_type in ("PROCEDURE", "FUNCTION", "TRIGGER")
                else SymbolType.TYPE
            )
            symbols.append(
                ExtractedSymbol(
                    name=raw_name,
                    symbol_type=sym_type,
                    qualified_name=raw_name,
                    start_line=start_line,
                    end_line=max(start_line, end_line),
                )
            )
        symbols.sort(key=lambda s: s.start_line)
        return symbols

    # Mask strings & comments
    masked = mask_comments_and_strings(code_str, language)
    n = len(masked)

    # 1. Map all matching brace pairs
    brace_stack: list[int] = []
    brace_pairs: dict[int, int] = {}
    for idx, ch in enumerate(masked):
        if ch == "{":
            brace_stack.append(idx)
        elif ch == "}":
            if brace_stack:
                open_idx = brace_stack.pop()
                brace_pairs[open_idx] = idx

    for open_idx in brace_stack:
        brace_pairs[open_idx] = n - 1

    containers: list[tuple[int, int, int, ExtractedSymbol]] = []
    functions: list[tuple[int, int, int, ExtractedSymbol]] = []

    # 2. Scan every `{` and check preceding header
    prev_boundary = 0
    i = 0
    while i < n:
        ch = masked[i]
        if ch == "{":
            open_idx = i
            close_idx = brace_pairs.get(open_idx, n - 1)
            header = masked[prev_boundary:open_idx].strip()
            header_clean = " ".join(header.split())

            container_match = None
            if language == "Rust" and "impl" in header_clean:
                r_match = RE_RUST_IMPL.search(header_clean)
                if r_match:
                    name = r_match.group(1)
                    container_match = ("impl", name)

            if not container_match:
                c_match = RE_CONTAINER.search(header_clean)
                if c_match:
                    container_match = (c_match.group(1), c_match.group(2))

            if container_match:
                kw, name = container_match
                sym_type = CONTAINER_KEYWORD_MAP.get(kw, SymbolType.CLASS)
                kw_pos = masked[prev_boundary:open_idx].find(kw)
                start_line = get_line_num(prev_boundary + (kw_pos if kw_pos != -1 else 0))
                end_line = get_line_num(close_idx)
                sym = ExtractedSymbol(
                    name=name,
                    symbol_type=sym_type,
                    qualified_name=name,
                    start_line=start_line,
                    end_line=max(start_line, end_line),
                )
                containers.append((prev_boundary, open_idx, close_idx, sym))
            else:
                if "(" in header_clean and ")" in header_clean:
                    paren_pos = header_clean.rfind("(")
                    pre_paren = header_clean[:paren_pos].strip().split()
                    if pre_paren:
                        fn_candidate = pre_paren[-1].lstrip("*&")
                        if fn_candidate not in CONTROL_FLOW_KEYWORDS and re.match(
                            r"^[A-Za-z0-9_]+$", fn_candidate
                        ):
                            fn_pos = masked[prev_boundary:open_idx].find(fn_candidate)
                            fn_start_idx = prev_boundary + (fn_pos if fn_pos != -1 else 0)
                            start_line = get_line_num(fn_start_idx)
                            end_line = get_line_num(close_idx)
                            fn_sym = ExtractedSymbol(
                                name=fn_candidate,
                                symbol_type=SymbolType.FUNCTION,
                                qualified_name=fn_candidate,
                                start_line=start_line,
                                end_line=max(start_line, end_line),
                            )
                            functions.append((prev_boundary, open_idx, close_idx, fn_sym))

            prev_boundary = i + 1
        elif ch in (";", "}"):
            prev_boundary = i + 1

        i += 1

    # 3. Handle Dart / JS Arrow methods: `name(...) => ...;`
    for m in RE_DART_ARROW.finditer(masked):
        name = m.group(2)
        if name not in CONTROL_FLOW_KEYWORDS:
            arrow_idx = m.end()
            semi_idx = masked.find(";", arrow_idx)
            if semi_idx != -1:
                start_line = get_line_num(m.start())
                end_line = get_line_num(semi_idx)
                fn_sym = ExtractedSymbol(
                    name=name,
                    symbol_type=SymbolType.FUNCTION,
                    qualified_name=name,
                    start_line=start_line,
                    end_line=max(start_line, end_line),
                )
                functions.append((m.start(), arrow_idx, semi_idx, fn_sym))

    # 4. Handle Shell functions: `name() { ... }` or `function name { ... }`
    if language in ("Shell", "Bash"):
        for m in RE_SHELL_FUNC.finditer(code_str):
            name = m.group(1) or m.group(2)
            if name:
                start_line = get_line_num(m.start())
                open_brace = code_str.find("{", m.start())
                close_brace = brace_pairs.get(open_brace, len(code_str) - 1)
                end_line = get_line_num(close_brace)
                fn_sym = ExtractedSymbol(
                    name=name,
                    symbol_type=SymbolType.FUNCTION,
                    qualified_name=name,
                    start_line=start_line,
                    end_line=max(start_line, end_line),
                )
                symbols.append(fn_sym)

    # 5. Assemble Hierarchy: Place methods inside containers
    containers.sort(key=lambda c: (c[1], -c[2]))

    for f_start, f_open, f_close, fn_sym in functions:
        enclosing_container = None
        for c_start, c_open, c_close, c_sym in containers:
            if c_open < f_open and f_close <= c_close:
                enclosing_container = c_sym

        if enclosing_container:
            fn_sym.symbol_type = SymbolType.METHOD
            fn_sym.qualified_name = f"{enclosing_container.name}.{fn_sym.name}"
            enclosing_container.children.append(fn_sym)
        else:
            symbols.append(fn_sym)

    for _, _, _, c_sym in containers:
        symbols.append(c_sym)

    symbols.sort(key=lambda s: s.start_line)
    return symbols
