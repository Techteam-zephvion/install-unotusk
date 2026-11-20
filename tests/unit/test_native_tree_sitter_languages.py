import importlib.machinery
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# Pre-load enums module directly to avoid loading all DB models during unit test
enums_mod = importlib.machinery.SourceFileLoader(
    "apps.api.src.models.enums", str(ROOT / "apps/api/src/models/enums.py")
).load_module()
sys.modules["apps.api.src.models.enums"] = enums_mod

from apps.api.src.services.parser.dependency_extractor import (
    extract_dependencies_from_tree,
)
from apps.api.src.services.parser.heuristics import (
    is_native_tree_sitter_target,
)
from apps.api.src.services.parser.symbol_extractor import (
    extract_symbols_from_tree,
)
from apps.api.src.services.parser.tree_sitter_parser import (
    get_parser,
    is_native_tree_sitter_candidate,
    parse_code,
)


class TestNativeTreeSitterLanguages(unittest.TestCase):
    def test_primary_languages_true_condition(self):
        """Verify that Python, TypeScript, JS, Go, Dart, Java, Rust, C++, C, C# are in the TRUE condition."""
        primary_langs = [
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
        ]
        for lang in primary_langs:
            self.assertTrue(is_native_tree_sitter_target(lang), f"{lang} should be in TRUE condition")
            self.assertTrue(is_native_tree_sitter_candidate(lang), f"{lang} candidate should be True")

    def test_secondary_languages_no_condition(self):
        """Verify that Kotlin, Swift, PHP, Ruby, etc. are in the NO condition (Universal Chunker)."""
        secondary_langs = [
            "Kotlin",
            "Swift",
            "PHP",
            "Ruby",
            "Shell",
            "SQL",
            "HTML",
            "Markdown",
            "YAML",
        ]
        for lang in secondary_langs:
            self.assertFalse(is_native_tree_sitter_target(lang), f"{lang} should be in NO condition")
            self.assertFalse(is_native_tree_sitter_candidate(lang), f"{lang} candidate should be False")
            self.assertIsNone(get_parser(lang), f"{lang} should return None for tree-sitter parser")

    def test_universal_fallback_for_secondary_languages(self):
        """Verify that secondary languages route cleanly through the Universal Parser."""
        kotlin_code = b"""
        package com.example.app

        import com.example.models.User
        import java.util.Date

        class UserManager(val db: Database) {
            fun getUserById(id: String): User {
                return db.find(id)
            }
        }
        """
        # Extract symbols for Kotlin (in NO condition)
        symbols = extract_symbols_from_tree(None, kotlin_code, "Kotlin")
        self.assertGreaterEqual(len(symbols), 1)
        sym_names = [s.name for s in symbols]
        self.assertTrue("UserManager" in sym_names or "getUserById" in sym_names)

        # Extract dependencies for Kotlin
        deps = extract_dependencies_from_tree(None, kotlin_code, "Kotlin")
        self.assertGreaterEqual(len(deps), 1)
        targets = [d.raw_target for d in deps]
        self.assertTrue(any("com.example.models.User" in t for t in targets))

    def test_universal_fallback_for_primary_languages_when_ast_unloaded(self):
        """Verify that even primary languages gracefully fall back to Universal Chunker when AST is None."""
        dart_code = b"""
        import 'package:flutter/material.dart';
        import '../services/auth_service.dart';

        class AuthScreen extends StatelessWidget {
          void handleLogin() {
            print("logging in");
          }
        }
        """
        symbols = extract_symbols_from_tree(None, dart_code, "Dart")
        self.assertGreaterEqual(len(symbols), 1)
        self.assertTrue(any(s.name == "AuthScreen" for s in symbols))

        deps = extract_dependencies_from_tree(None, dart_code, "Dart")
        self.assertGreaterEqual(len(deps), 2)
        self.assertTrue(any("package:flutter/material.dart" in d.raw_target for d in deps))
        self.assertTrue(any("auth_service.dart" in d.raw_target for d in deps))

    def test_native_tree_sitter_rust_parsing(self):
        """Verify native tree-sitter symbol and dependency extraction for Rust."""
        rust_code = b"""
        use std::sync::Arc;
        use crate::config::ServerConfig;

        pub struct ConnectionPool {
            size: usize,
        }

        pub fn create_pool() -> ConnectionPool {
            ConnectionPool { size: 10 }
        }
        """
        tree = parse_code(rust_code, "Rust")
        symbols = extract_symbols_from_tree(tree, rust_code, "Rust")
        self.assertGreaterEqual(len(symbols), 2)
        sym_names = [s.name for s in symbols]
        self.assertIn("ConnectionPool", sym_names)
        self.assertIn("create_pool", sym_names)

        deps = extract_dependencies_from_tree(tree, rust_code, "Rust")
        self.assertGreaterEqual(len(deps), 2)
        raw_deps = [d.raw_target for d in deps]
        self.assertTrue(any("std::sync::Arc" in r for r in raw_deps))
        self.assertTrue(any("crate::config::ServerConfig" in r for r in raw_deps))

    def test_native_tree_sitter_java_parsing(self):
        """Verify native tree-sitter symbol and dependency extraction for Java."""
        java_code = b"""
        package com.unotusk.service;
        import java.util.List;
        import com.unotusk.model.User;

        public class UserService {
            public User findUser(String id) {
                return null;
            }
        }
        """
        tree = parse_code(java_code, "Java")
        symbols = extract_symbols_from_tree(tree, java_code, "Java")
        self.assertGreaterEqual(len(symbols), 1)
        sym_names = [s.name for s in symbols]
        self.assertIn("UserService", sym_names)

        deps = extract_dependencies_from_tree(tree, java_code, "Java")
        self.assertGreaterEqual(len(deps), 2)
        raw_deps = [d.raw_target for d in deps]
        self.assertTrue(any("java.util.List" in r for r in raw_deps))
        self.assertTrue(any("com.unotusk.model.User" in r for r in raw_deps))

    def test_native_tree_sitter_csharp_parsing(self):
        """Verify native tree-sitter symbol and dependency extraction for C#."""
        cs_code = b"""
        using System;
        using System.Collections.Generic;

        namespace Unotusk.App {
            public class PaymentProcessor {
                public void ProcessPayment() {}
            }
        }
        """
        tree = parse_code(cs_code, "C#")
        symbols = extract_symbols_from_tree(tree, cs_code, "C#")
        self.assertGreaterEqual(len(symbols), 1)
        sym_names = [s.name for s in symbols]
        self.assertIn("PaymentProcessor", sym_names)

        deps = extract_dependencies_from_tree(tree, cs_code, "C#")
        self.assertGreaterEqual(len(deps), 2)
        raw_deps = [d.raw_target for d in deps]
        self.assertTrue(any("System" in r for r in raw_deps))
        self.assertTrue(any("System.Collections.Generic" in r for r in raw_deps))

    def test_native_tree_sitter_cpp_parsing(self):
        """Verify native tree-sitter symbol and dependency extraction for C++."""
        cpp_code = b"""
        #include <vector>
        #include "engine/core.h"

        class GameEngine {
        public:
            void init();
        };

        void run_simulation() {}
        """
        tree = parse_code(cpp_code, "C++")
        symbols = extract_symbols_from_tree(tree, cpp_code, "C++")
        self.assertGreaterEqual(len(symbols), 2)
        sym_names = [s.name for s in symbols]
        self.assertIn("GameEngine", sym_names)
        self.assertIn("run_simulation", sym_names)

        deps = extract_dependencies_from_tree(tree, cpp_code, "C++")
        self.assertGreaterEqual(len(deps), 2)
        raw_deps = [d.raw_target for d in deps]
        self.assertTrue(any("vector" in r for r in raw_deps))
        self.assertTrue(any("engine/core.h" in r for r in raw_deps))


if __name__ == "__main__":
    unittest.main()
