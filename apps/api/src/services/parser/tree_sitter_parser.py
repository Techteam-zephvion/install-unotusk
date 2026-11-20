import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import tree_sitter
    _TREE_SITTER_AVAILABLE = True
except ImportError:
    tree_sitter = None  # type: ignore[assignment]
    _TREE_SITTER_AVAILABLE = False

# Import language grammar bindings gracefully
def _safe_import(mod_name: str) -> Any:
    try:
        return __import__(mod_name)
    except ImportError:
        return None

tree_sitter_python = _safe_import("tree_sitter_python")
tree_sitter_typescript = _safe_import("tree_sitter_typescript")
tree_sitter_javascript = _safe_import("tree_sitter_javascript")
tree_sitter_go = _safe_import("tree_sitter_go")
tree_sitter_java = _safe_import("tree_sitter_java")
tree_sitter_rust = _safe_import("tree_sitter_rust")
tree_sitter_cpp = _safe_import("tree_sitter_cpp")
tree_sitter_c = _safe_import("tree_sitter_c")
tree_sitter_c_sharp = _safe_import("tree_sitter_c_sharp")
tree_sitter_dart = _safe_import("tree_sitter_dart")

# Primary Main Languages for Native Tree-sitter (TRUE condition in flowchart)
PRIMARY_TREE_SITTER_LANGUAGES = {
    "Python",
    "TypeScript",
    "TypeScript/TSX",
    "JavaScript",
    "JavaScript/JSX",
    "Go",
    "Dart",
    "Java",
    "Rust",
    "C++",
    "C++ Header",
    "C",
    "C/C++ Header",
    "C#",
}

_parsers: dict[str, Any] = {}
_initialized = False


def is_native_tree_sitter_candidate(language: str) -> bool:
    """Returns True if language belongs to the primary main languages group (TRUE condition).
    Secondary languages return False and go directly to Universal Chunker (NO condition)."""
    return language in PRIMARY_TREE_SITTER_LANGUAGES


def init_parsers() -> None:
    global _parsers, _initialized
    if not _TREE_SITTER_AVAILABLE or _initialized:
        return

    _initialized = True

    # Python
    if tree_sitter_python:
        try:
            py_lang = tree_sitter.Language(tree_sitter_python.language())
            _parsers["Python"] = tree_sitter.Parser(py_lang)
        except Exception as e:
            logger.warning("Error initializing Tree-sitter Python: %s", e)

    # TypeScript & TSX
    if tree_sitter_typescript:
        try:
            tsx_lang = tree_sitter.Language(tree_sitter_typescript.language_tsx())
            tsx_parser = tree_sitter.Parser(tsx_lang)
            _parsers["TypeScript"] = tsx_parser
            _parsers["TypeScript/TSX"] = tsx_parser
        except Exception as e:
            logger.warning("Error initializing Tree-sitter TypeScript: %s", e)

    # JavaScript & JSX
    if tree_sitter_javascript:
        try:
            js_lang = tree_sitter.Language(tree_sitter_javascript.language())
            _parsers["JavaScript"] = tree_sitter.Parser(js_lang)
            _parsers["JavaScript/JSX"] = tree_sitter.Parser(js_lang)
        except Exception as e:
            logger.warning("Error initializing Tree-sitter JavaScript: %s", e)

    # Go
    if tree_sitter_go:
        try:
            go_lang = tree_sitter.Language(tree_sitter_go.language())
            _parsers["Go"] = tree_sitter.Parser(go_lang)
        except Exception as e:
            logger.warning("Error initializing Tree-sitter Go: %s", e)

    # Java
    if tree_sitter_java:
        try:
            java_lang = tree_sitter.Language(tree_sitter_java.language())
            _parsers["Java"] = tree_sitter.Parser(java_lang)
        except Exception as e:
            logger.warning("Error initializing Tree-sitter Java: %s", e)

    # Rust
    if tree_sitter_rust:
        try:
            rust_lang = tree_sitter.Language(tree_sitter_rust.language())
            _parsers["Rust"] = tree_sitter.Parser(rust_lang)
        except Exception as e:
            logger.warning("Error initializing Tree-sitter Rust: %s", e)

    # C++
    if tree_sitter_cpp:
        try:
            cpp_lang = tree_sitter.Language(tree_sitter_cpp.language())
            cpp_parser = tree_sitter.Parser(cpp_lang)
            _parsers["C++"] = cpp_parser
            _parsers["C++ Header"] = cpp_parser
        except Exception as e:
            logger.warning("Error initializing Tree-sitter C++: %s", e)

    # C
    if tree_sitter_c:
        try:
            c_lang = tree_sitter.Language(tree_sitter_c.language())
            c_parser = tree_sitter.Parser(c_lang)
            _parsers["C"] = c_parser
            _parsers["C/C++ Header"] = c_parser
        except Exception as e:
            logger.warning("Error initializing Tree-sitter C: %s", e)

    # C#
    if tree_sitter_c_sharp:
        try:
            cs_lang = tree_sitter.Language(tree_sitter_c_sharp.language())
            _parsers["C#"] = tree_sitter.Parser(cs_lang)
        except Exception as e:
            logger.warning("Error initializing Tree-sitter C#: %s", e)

    # Dart
    if tree_sitter_dart:
        try:
            dart_lang = tree_sitter.Language(tree_sitter_dart.language())
            _parsers["Dart"] = tree_sitter.Parser(dart_lang)
        except Exception as e:
            logger.warning("Error initializing Tree-sitter Dart: %s", e)


def get_parser(language: str) -> Any | None:
    """Retrieve Tree-sitter parser for supported primary language, or None if unsupported / secondary."""
    if not is_native_tree_sitter_candidate(language):
        # Secondary language (Kotlin, Swift, PHP, Ruby, etc.) -> NO condition
        return None
    init_parsers()
    return _parsers.get(language)


def parse_code(code_bytes: bytes, language: str) -> Any | None:
    """Parse source code bytes into AST tree using appropriate language parser.
    Returns AST tree if native parser is available, or None for Universal Fallback."""
    if not _TREE_SITTER_AVAILABLE or not is_native_tree_sitter_candidate(language):
        return None
    parser = get_parser(language)
    if parser is None:
        return None
    try:
        return parser.parse(code_bytes)
    except Exception as e:
        logger.debug("Tree-sitter parse exception for %s: %s", language, e)
        return None
