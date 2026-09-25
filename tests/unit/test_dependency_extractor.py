from apps.api.src.models.enums import DependencyType
from apps.api.src.services.parser.dependency_extractor import extract_dependencies_from_tree
from apps.api.src.services.parser.tree_sitter_parser import parse_code


def test_python_dependency_extraction():
    code = b"""
import os
import sys
from .local_module import helper_fn
from fastapi import FastAPI, Depends
"""
    tree = parse_code(code, "Python")
    assert tree is not None
    deps = extract_dependencies_from_tree(tree, code, "Python")

    targets = [d.raw_target for d in deps]
    assert "os" in targets
    assert "sys" in targets
    assert ".local_module" in targets
    assert "fastapi" in targets

    rel_dep = next(d for d in deps if d.raw_target == ".local_module")
    assert rel_dep.is_relative is True
    assert rel_dep.dependency_type == DependencyType.FROM_IMPORT

    ext_dep = next(d for d in deps if d.raw_target == "fastapi")
    assert ext_dep.is_relative is False


def test_typescript_dependency_extraction():
    code = b"""
import React from 'react';
import { Button } from './components/Button';
import { User } from '@/types';
const logger = require('pino');
"""
    tree = parse_code(code, "TypeScript")
    assert tree is not None
    deps = extract_dependencies_from_tree(tree, code, "TypeScript")

    targets = [d.raw_target for d in deps]
    assert "react" in targets
    assert "./components/Button" in targets
    assert "@/types" in targets
    assert "pino" in targets

    btn_dep = next(d for d in deps if d.raw_target == "./components/Button")
    assert btn_dep.is_relative is True

    pkg_dep = next(d for d in deps if d.raw_target == "react")
    assert pkg_dep.is_relative is False


def test_python_qualified_import_extraction():
    code = b"""
import math
import a.b.c
import apps.api.src.models.user
import os, sys, foo.bar.baz as fbb
"""
    # For Python, AST parsing is used directly without requiring Tree-sitter tree
    deps = extract_dependencies_from_tree(None, code, "Python")
    targets = [d.raw_target for d in deps]

    # Verify complete import paths are preserved
    assert "math" in targets
    assert "a.b.c" in targets
    assert "apps.api.src.models.user" in targets
    assert "os" in targets
    assert "sys" in targets
    assert "foo.bar.baz" in targets

    # Verify not truncated to first dot segment
    assert "a" not in targets
    assert "apps" not in targets
    assert "foo" not in targets

    # Verify dependency attributes
    math_dep = next(d for d in deps if d.raw_target == "math")
    assert math_dep.is_relative is False
    assert math_dep.dependency_type == DependencyType.IMPORT

    abc_dep = next(d for d in deps if d.raw_target == "a.b.c")
    assert abc_dep.is_relative is False
    assert abc_dep.dependency_type == DependencyType.IMPORT

    user_dep = next(d for d in deps if d.raw_target == "apps.api.src.models.user")
    assert user_dep.is_relative is False
    assert user_dep.dependency_type == DependencyType.IMPORT


def test_python_qualified_import_resolution():
    import os
    from unittest.mock import MagicMock

    code = b"""
import math
import a.b.c
import apps.api.src.models.user
import urllib.request
"""
    deps = extract_dependencies_from_tree(None, code, "Python")

    # Simulate repository files map in IngestionService
    mock_file_user = MagicMock()
    mock_file_user.id = "user-file-uuid"
    mock_file_abc = MagicMock()
    mock_file_abc.id = "abc-file-uuid"

    created_files_map = {
        "apps/api/src/models/user.py": mock_file_user,
        "src/a/b/c.py": mock_file_abc,
    }

    # Resolution logic from IngestionService (apps/api/src/services/ingestion_service.py:341-347)
    resolved: dict[str, str | None] = {}
    for dep in deps:
        target_file_id = None
        if not dep.is_relative:
            for p, rf in created_files_map.items():
                p_no_ext = os.path.splitext(p)[0]
                target_as_path = dep.raw_target.replace(".", "/")
                if p_no_ext == target_as_path or p_no_ext.endswith(target_as_path):
                    target_file_id = rf.id
                    break
        resolved[dep.raw_target] = target_file_id

    # 1. Target internal files are correctly identified
    assert resolved["apps.api.src.models.user"] == "user-file-uuid"
    assert resolved["a.b.c"] == "abc-file-uuid"

    # 2. External packages (with or without dots) are NOT treated as internal files
    assert resolved["math"] is None
    assert resolved["urllib.request"] is None

