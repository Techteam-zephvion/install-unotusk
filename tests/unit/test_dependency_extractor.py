from apps.api.src.models.enums import DependencyType
from apps.api.src.services.parser.dependency_extractor import extract_dependencies_from_tree
from apps.api.src.services.parser.tree_sitter_parser import _TREE_SITTER_AVAILABLE, parse_code


def test_python_dependency_extraction():
    code = b"""
import os
import sys
from .local_module import helper_fn
from fastapi import FastAPI, Depends
"""
    tree = parse_code(code, "Python")
    if _TREE_SITTER_AVAILABLE:
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
    if _TREE_SITTER_AVAILABLE:
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


def test_typescript_dependency_extraction_robustness():
    """Verify zero false positives from comments/strings and support for all JS/TS import patterns."""
    code = b"""
// 1. Single line comment: import fake1 from 'fake1';
// const reqFake = require('fake_req_1');
/* 2. Block comment: import fake2 from 'fake2'; */
/*
 * 3. Multi-line comment
 * const fake3 = require('fake3');
 * import fake4 from "fake4";
 */
const str1 = "import fake5 from 'fake5'";
const str2 = 'require("fake6")';
const str3 = `import fake7 from 'fake7'`;

import React from 'react';
import type { FC } from 'react';
import {
  Button,
  type ButtonProps
} from './components/Button';
import * as utils from '../utils';
import '@/styles.css';
import "~/styles/global.css";
export { helper } from './helper';
export * from 'lodash';
export const a = 1;
const pino = require('pino');
const local = require('./local');
const dynamic = import('./dynamic');
import tsreq = require('ts-pkg');
"""
    deps = extract_dependencies_from_tree(None, code, "TypeScript")

    target_map = {d.raw_target: d for d in deps}

    # Verify no false positives from comments or strings
    for i in range(1, 8):
        assert f"fake{i}" not in target_map
    assert "fake_req_1" not in target_map

    # Verify valid targets are captured
    assert "react" in target_map
    assert "./components/Button" in target_map
    assert "../utils" in target_map
    assert "@/styles.css" in target_map
    assert "~/styles/global.css" in target_map
    assert "./helper" in target_map
    assert "lodash" in target_map
    assert "pino" in target_map
    assert "./local" in target_map
    assert "./dynamic" in target_map
    assert "ts-pkg" in target_map

    # Check relative vs package flags
    assert target_map["./components/Button"].is_relative is True
    assert target_map["../utils"].is_relative is True
    assert target_map["@/styles.css"].is_relative is True
    assert target_map["~/styles/global.css"].is_relative is True
    assert target_map["react"].is_relative is False
    assert target_map["lodash"].is_relative is False
    assert target_map["pino"].is_relative is False

    # Check dependency types
    assert target_map["pino"].dependency_type == DependencyType.REQUIRE
    assert target_map["./local"].dependency_type == DependencyType.REQUIRE
    assert target_map["react"].dependency_type == DependencyType.IMPORT
    assert target_map["./dynamic"].dependency_type == DependencyType.IMPORT

    # Check accurate line numbers
    react_lines = [d.line_number for d in deps if d.raw_target == "react"]
    assert react_lines == [14, 15]
    assert target_map["./components/Button"].line_number == 16
    assert target_map["pino"].line_number == 26


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
