import os
from pathlib import Path

# Configurable excluded directories
EXCLUDED_DIRECTORIES = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    "out",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".turbo",
    ".gradle",
    ".idea",
    ".vscode",
    ".dart_tool",
    "target",
}

# Binary extensions
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".pdf", ".exe", ".bin", ".tar", ".gz", ".zip", ".7z",
    ".pyc", ".pyo", ".pyd", ".so", ".dylib", ".dll", ".whl",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".mp4", ".mov", ".avi", ".mp3", ".wav",
    ".jar", ".war", ".class",
}

# Lock / Generated files
GENERATED_OR_LOCK_FILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "pipfile.lock",
    "cargo.lock",
    "composer.lock",
    "gemfile.lock",
}

# Extension to language map
EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript/TSX",
    ".js": "JavaScript",
    ".jsx": "JavaScript/JSX",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".go": "Go",
    ".java": "Java",
    ".rs": "Rust",
    ".sql": "SQL",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".md": "Markdown",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".xml": "XML",
    ".toml": "TOML",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".dart": "Dart",
    ".rb": "Ruby",
    ".php": "PHP",
}

# Parser supported languages (Tree-sitter)
PARSER_SUPPORTED_LANGUAGES = {
    "Python",
    "TypeScript",
    "TypeScript/TSX",
    "JavaScript",
    "JavaScript/JSX",
    "Go",
}


def is_path_excluded(relative_path: str) -> bool:
    """Check if relative file or directory path matches any exclusion rule."""
    parts = Path(relative_path).parts
    for part in parts:
        if part in EXCLUDED_DIRECTORIES:
            return True
        if part.startswith(".") and len(part) > 1 and part not in (".github",):
            # Exclude other hidden directories like .cache, .tox, etc.
            return True
    return False


def detect_language(filename: str) -> str:
    """Determine language via extension and filename heuristics."""
    ext = os.path.splitext(filename)[1].lower()
    return EXTENSION_LANGUAGE_MAP.get(ext, "UNKNOWN")


def is_file_binary(filename: str) -> bool:
    """Check whether a file is binary based on extension."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in BINARY_EXTENSIONS


def is_file_generated(filename: str) -> bool:
    """Check if file is a lockfile or minified/generated file."""
    base = os.path.basename(filename).lower()
    if base in GENERATED_OR_LOCK_FILES:
        return True
    if ".min." in base or ".generated." in base:
        return True
    return False


def is_file_test(relative_path: str) -> bool:
    """Check if file is a test file based on naming and directory conventions."""
    path_lower = relative_path.lower()
    if "test" in path_lower or "spec" in path_lower:
        return True
    base = os.path.basename(path_lower)
    if base.startswith("test_") or base.endswith("_test.py") or base.endswith(".test.ts") or base.endswith(".spec.ts"):
        return True
    return False
