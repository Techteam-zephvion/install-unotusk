from apps.api.src.services.parser.heuristics import (
    detect_language,
    is_file_binary,
    is_file_generated,
    is_file_test,
    is_path_excluded,
)


def test_language_detection():
    assert detect_language("main.py") == "Python"
    assert detect_language("app.ts") == "TypeScript"
    assert detect_language("component.tsx") == "TypeScript/TSX"
    assert detect_language("index.js") == "JavaScript"
    assert detect_language("server.go") == "Go"
    assert detect_language("Main.java") == "Java"
    assert detect_language("lib.rs") == "Rust"
    assert detect_language("query.sql") == "SQL"
    assert detect_language("readme.md") == "Markdown"
    assert detect_language("unknown.xyz123") == "UNKNOWN"


def test_path_exclusion():
    assert is_path_excluded("node_modules/react/index.js") is True
    assert is_path_excluded(".git/config") is True
    assert is_path_excluded(".venv/lib/python3.12/site.py") is True
    assert is_path_excluded("dist/bundle.js") is True
    assert is_path_excluded("build/output.css") is True
    assert is_path_excluded("src/components/Navbar.tsx") is False
    assert is_path_excluded("apps/api/src/main.py") is False


def test_binary_and_generated_checks():
    assert is_file_binary("logo.png") is True
    assert is_file_binary("archive.tar.gz") is True
    assert is_file_binary("app.py") is False

    assert is_file_generated("package-lock.json") is True
    assert is_file_generated("yarn.lock") is True
    assert is_file_generated("bundle.min.js") is True
    assert is_file_generated("package.json") is False


def test_is_test_heuristics():
    assert is_file_test("tests/unit/test_auth.py") is True
    assert is_file_test("src/components/Button.spec.ts") is True
    assert is_file_test("src/models/user.py") is False
