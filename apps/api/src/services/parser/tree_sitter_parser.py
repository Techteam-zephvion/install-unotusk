from typing import Any

try:
    import tree_sitter
    _TREE_SITTER_AVAILABLE = True
except ImportError:
    tree_sitter = None  # type: ignore[assignment]
    _TREE_SITTER_AVAILABLE = False

_parsers: dict[str, Any] = {}


def init_parsers() -> None:
    global _parsers
    if not _TREE_SITTER_AVAILABLE or _parsers:
        return

    # Python
    try:
        import tree_sitter_python
        py_lang = tree_sitter.Language(tree_sitter_python.language())
        _parsers["Python"] = tree_sitter.Parser(py_lang)
    except Exception:
        pass

    # TypeScript & TSX (language_tsx parses both standard TypeScript and TSX syntax safely)
    try:
        import tree_sitter_typescript
        tsx_lang = tree_sitter.Language(tree_sitter_typescript.language_tsx())
        tsx_parser = tree_sitter.Parser(tsx_lang)
        _parsers["TypeScript"] = tsx_parser
        _parsers["TypeScript/TSX"] = tsx_parser
    except Exception:
        pass

    # JavaScript & JSX
    try:
        import tree_sitter_javascript
        js_lang = tree_sitter.Language(tree_sitter_javascript.language())
        _parsers["JavaScript"] = tree_sitter.Parser(js_lang)
        _parsers["JavaScript/JSX"] = tree_sitter.Parser(js_lang)
    except Exception:
        pass

    # Go
    try:
        import tree_sitter_go
        go_lang = tree_sitter.Language(tree_sitter_go.language())
        _parsers["Go"] = tree_sitter.Parser(go_lang)
    except Exception:
        pass

    # Optional parsers for extended languages (Tier 1 AST if package installed)
    try:
        import tree_sitter_java
        java_lang = tree_sitter.Language(tree_sitter_java.language())
        _parsers["Java"] = tree_sitter.Parser(java_lang)
    except Exception:
        pass

    try:
        import tree_sitter_rust
        rust_lang = tree_sitter.Language(tree_sitter_rust.language())
        _parsers["Rust"] = tree_sitter.Parser(rust_lang)
    except Exception:
        pass

    try:
        import tree_sitter_c_sharp
        cs_lang = tree_sitter.Language(tree_sitter_c_sharp.language())
        _parsers["C#"] = tree_sitter.Parser(cs_lang)
    except Exception:
        pass

    try:
        import tree_sitter_cpp
        cpp_lang = tree_sitter.Language(tree_sitter_cpp.language())
        cpp_parser = tree_sitter.Parser(cpp_lang)
        _parsers["C++"] = cpp_parser
        _parsers["C++ Header"] = cpp_parser
    except Exception:
        pass

    try:
        import tree_sitter_c
        c_lang = tree_sitter.Language(tree_sitter_c.language())
        c_parser = tree_sitter.Parser(c_lang)
        _parsers["C"] = c_parser
        _parsers["C/C++ Header"] = c_parser
    except Exception:
        pass

    try:
        import tree_sitter_dart
        dart_lang = tree_sitter.Language(tree_sitter_dart.language())
        _parsers["Dart"] = tree_sitter.Parser(dart_lang)
    except Exception:
        pass


def get_parser(language: str) -> Any | None:
    """Retrieve Tree-sitter parser for supported language, or None if unsupported."""
    init_parsers()
    return _parsers.get(language)


def parse_code(code_bytes: bytes, language: str) -> Any | None:
    """Parse source code bytes into AST tree using appropriate language parser."""
    if not _TREE_SITTER_AVAILABLE:
        return None
    parser = get_parser(language)
    if parser is None:
        return None
    try:
        return parser.parse(code_bytes)
    except Exception:
        return None
