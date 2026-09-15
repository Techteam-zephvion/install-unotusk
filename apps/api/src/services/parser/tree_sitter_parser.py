import tree_sitter
import tree_sitter_go
import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_typescript

_parsers: dict[str, tree_sitter.Parser] = {}


def init_parsers() -> None:
    global _parsers
    if _parsers:
        return

    try:
        # Python
        py_lang = tree_sitter.Language(tree_sitter_python.language())
        _parsers["Python"] = tree_sitter.Parser(py_lang)

        # TypeScript
        ts_lang = tree_sitter.Language(tree_sitter_typescript.language_typescript())
        _parsers["TypeScript"] = tree_sitter.Parser(ts_lang)

        # TSX
        tsx_lang = tree_sitter.Language(tree_sitter_typescript.language_tsx())
        _parsers["TypeScript/TSX"] = tree_sitter.Parser(tsx_lang)

        # JavaScript & JSX
        js_lang = tree_sitter.Language(tree_sitter_javascript.language())
        _parsers["JavaScript"] = tree_sitter.Parser(js_lang)
        _parsers["JavaScript/JSX"] = tree_sitter.Parser(js_lang)

        # Go
        go_lang = tree_sitter.Language(tree_sitter_go.language())
        _parsers["Go"] = tree_sitter.Parser(go_lang)
    except Exception as e:
        # Gracefully handle parser loading issues
        print(f"Warning: Error initializing Tree-sitter parsers: {e}")


def get_parser(language: str) -> tree_sitter.Parser | None:
    """Retrieve Tree-sitter parser for supported language, or None if unsupported."""
    init_parsers()
    return _parsers.get(language)


def parse_code(code_bytes: bytes, language: str) -> tree_sitter.Tree | None:
    """Parse source code bytes into AST tree using appropriate language parser."""
    parser = get_parser(language)
    if parser is None:
        return None
    try:
        return parser.parse(code_bytes)
    except Exception:
        return None
