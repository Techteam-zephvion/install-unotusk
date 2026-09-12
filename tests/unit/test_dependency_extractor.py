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
