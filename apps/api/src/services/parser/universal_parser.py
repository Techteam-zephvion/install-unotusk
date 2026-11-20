from __future__ import annotations

import re
from typing import Any

from apps.api.src.models.enums import DependencyType, SymbolType
from apps.api.src.services.parser.dependency_extractor import ExtractedDependency
from apps.api.src.services.parser.symbol_extractor import ExtractedSymbol

# Regex patterns for structural symbols across C-family, Rust, Swift, and modern languages
CLASS_PATTERN = re.compile(
    r"^\s*(?:(?:public|private|protected|abstract|final|static|open|sealed|data|internal|pub(?:\([^\)]+\))?)\s+)*"
    r"(?:class|interface|struct|trait|protocol|enum|mixin)\s+([A-Za-z0-9_]+)",
    re.MULTILINE,
)

FUNCTION_PATTERN = re.compile(
    r"^\s*(?:(?:public|private|protected|static|async|override|final|inline|const|virtual|mut|pub(?:\([^\)]+\))?)\s+)*"
    r"(?:def|fn|func|function|fun|void|[A-Za-z0-9_<>,\[\]]+)\s+([A-Za-z0-9_]+)\s*\([^\)]*\)\s*(?:->\s*[A-Za-z0-9_<>,\[\]]+)?\s*(?:async\s*)?\{?",
    re.MULTILINE,
)

IMPORT_PATTERNS = [
    # Dart: import 'package:flutter/material.dart';
    re.compile(r"^\s*(?:import|export)\s+['\"]([^'\"]+)['\"];?", re.MULTILINE),
    # Java / Kotlin: import java.util.List;
    re.compile(r"^\s*import\s+(?:static\s+)?([A-Za-z0-9_.*]+);?", re.MULTILINE),
    # Rust: use std::sync::Arc;
    re.compile(r"^\s*use\s+([A-Za-z0-9_:]+);?", re.MULTILINE),
    # C/C++: #include <vector> or #include "header.h"
    re.compile(r"^\s*#include\s+[<'\"]([^>'\"]+)[>'\"]", re.MULTILINE),
    # Swift / Python / Ruby / PHP: import SwiftUI / require 'net/http' / use App\Models\User
    re.compile(r"^\s*(?:import|require|require_relative|use)\s+([A-Za-z0-9_\\/.]+);?", re.MULTILINE),
]


def _find_matching_brace_end(lines: list[str], start_line_idx: int) -> int:
    """Finds the ending line index for a code block delimited by curly braces."""
    brace_depth = 0
    found_open = False

    for idx in range(start_line_idx, len(lines)):
        line = lines[idx]
        # Ignore comments
        stripped = line.split("//")[0].split("#")[0]

        for char in stripped:
            if char == "{":
                brace_depth += 1
                found_open = True
            elif char == "}":
                brace_depth -= 1
                if found_open and brace_depth <= 0:
                    return idx + 1  # 1-based line number

    # Fallback to reasonable block boundary
    return min(len(lines), start_line_idx + 30)


def extract_universal_symbols(code_bytes: bytes, language: str) -> list[ExtractedSymbol]:
    """
    Universal Symbol Extractor (Phase B):
    Extracts classes, interfaces, structs, and methods from any language using regex and brace parsing.
    """
    symbols: list[ExtractedSymbol] = []
    text = code_bytes.decode("utf-8", errors="replace").replace("\x00", "")
    lines = text.splitlines()
    if not lines:
        return symbols

    i = 0
    while i < len(lines):
        line = lines[i]
        line_num = i + 1

        # Skip comment lines
        stripped = line.strip()
        if stripped.startswith(("//", "/*", "*", "#", "///", "/**")):
            i += 1
            continue

        # 1. Match Class / Interface / Struct / Trait / Enum
        class_match = CLASS_PATTERN.search(line)
        if class_match:
            class_name = class_match.group(1)
            raw_match = class_match.group(0).lower()
            sym_type = SymbolType.CLASS
            if "interface" in raw_match or "protocol" in raw_match:
                sym_type = SymbolType.INTERFACE
            elif "struct" in raw_match or "trait" in raw_match:
                sym_type = SymbolType.TYPE
            elif "enum" in raw_match:
                sym_type = SymbolType.ENUM

            end_line = _find_matching_brace_end(lines, i)
            class_sym = ExtractedSymbol(
                name=class_name,
                symbol_type=sym_type,
                qualified_name=class_name,
                start_line=line_num,
                end_line=end_line,
            )

            # Extract child methods inside this class block
            if end_line > line_num + 1:
                class_lines = lines[i : end_line - 1]
                for c_idx, c_line in enumerate(class_lines):
                    if c_idx == 0:
                        continue  # Skip class declaration line itself
                    m_match = FUNCTION_PATTERN.search(c_line)
                    if m_match:
                        m_name = m_match.group(1)
                        if m_name not in ("if", "for", "while", "switch", "catch", "return", "new"):
                            m_start = line_num + c_idx
                            m_end = _find_matching_brace_end(lines, i + c_idx)
                            class_sym.children.append(
                                ExtractedSymbol(
                                    name=m_name,
                                    symbol_type=SymbolType.METHOD,
                                    qualified_name=f"{class_name}.{m_name}",
                                    start_line=m_start,
                                    end_line=min(m_end, end_line),
                                )
                            )

            symbols.append(class_sym)
            i = max(i + 1, end_line)
            continue

        # 2. Match Top-level Functions
        fn_match = FUNCTION_PATTERN.search(line)
        if fn_match:
            fn_name = fn_match.group(1)
            if fn_name not in ("if", "for", "while", "switch", "catch", "return", "new", "class"):
                end_line = _find_matching_brace_end(lines, i)
                symbols.append(
                    ExtractedSymbol(
                        name=fn_name,
                        symbol_type=SymbolType.FUNCTION,
                        qualified_name=fn_name,
                        start_line=line_num,
                        end_line=end_line,
                    )
                )
                i = max(i + 1, end_line)
                continue

        i += 1

    return symbols


def extract_universal_dependencies(code_bytes: bytes, language: str) -> list[ExtractedDependency]:
    """
    Universal Import Extractor (Phase B):
    Extracts module and package dependencies via universal regex patterns.
    """
    deps: list[ExtractedDependency] = []
    text = code_bytes.decode("utf-8", errors="replace").replace("\x00", "")
    lines = text.splitlines()

    for idx, line in enumerate(lines):
        line_num = idx + 1
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "#", "/*")):
            continue

        for pattern in IMPORT_PATTERNS:
            match = pattern.search(line)
            if match:
                raw_target = match.group(1).strip()
                # Clean package name
                target = raw_target.split(";")[0].strip()
                if target:
                    deps.append(
                        ExtractedDependency(
                            raw_target=target,
                            dependency_type=DependencyType.IMPORT,
                            line_number=line_num,
                        )
                    )
                break  # Only one import match per line

    return deps
