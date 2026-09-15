import re
from typing import Any

from apps.api.src.models.enums import (
    FindingCategory,
    FindingConfidence,
    FindingSeverity,
    SymbolType,
)
from apps.api.src.services.discovery_engine.base import (
    CandidateFinding,
    DiscoveryAnalyzer,
    DiscoveryContext,
)

IGNORED_FILE_PATTERNS = [
    "test",
    "spec",
    "conftest",
    "migration",
    "alembic",
    "main.py",
    "index.ts",
    "index.js",
    "app.py",
    "server.ts",
    "setup.py",
]

IGNORED_SYMBOL_NAMES = {
    "__init__",
    "__str__",
    "__repr__",
    "main",
    "run",
    "setup",
    "tearDown",
    "setUp",
    "handler",
    "process",
    "default",
}


class UnusedCodeAnalyzer(DiscoveryAnalyzer):
    @property
    def category(self) -> FindingCategory:
        return FindingCategory.UNUSED_CODE

    async def analyze(self, ctx: DiscoveryContext) -> list[CandidateFinding]:
        findings: list[CandidateFinding] = []

        # 1. Index all code content by file to search for symbol references
        chunk_content_by_file: dict[str, list[str]] = {}
        for chunk in ctx.chunks:
            if chunk.path not in chunk_content_by_file:
                chunk_content_by_file[chunk.path] = []
            chunk_content_by_file[chunk.path].append(chunk.content)

        # 2. Iterate through candidate symbols
        for sym in ctx.symbols:
            if sym.symbol_type not in (SymbolType.CLASS, SymbolType.FUNCTION, SymbolType.INTERFACE):
                continue

            # Skip common names and short names
            if len(sym.name) < 4 or sym.name in IGNORED_SYMBOL_NAMES:
                continue

            file_obj = ctx.file_by_id.get(sym.file_id)
            if not file_obj:
                continue

            # Skip test files and entry points
            path_lower = file_obj.path.lower()
            if any(ign in path_lower for ign in IGNORED_FILE_PATTERNS):
                continue

            # Count occurrences in other files
            has_reference = False
            for other_path, contents in chunk_content_by_file.items():
                if other_path == file_obj.path:
                    continue

                for content in contents:
                    # Match exact word boundary of symbol name
                    if re.search(r"\b" + re.escape(sym.name) + r"\b", content):
                        has_reference = True
                        break
                if has_reference:
                    break

            if not has_reference:
                # Also check dependencies
                sym_lower = sym.name.lower()
                if sym_lower in ctx.inbound_deps_by_target:
                    has_reference = True

            if not has_reference:
                evidence: list[dict[str, Any]] = [
                    {
                        "type": "symbol_definition",
                        "file": file_obj.path,
                        "symbol": sym.name,
                        "lines": f"{sym.start_line}-{sym.end_line}",
                        "snippet": f"Declared in {file_obj.path} (Lines {sym.start_line}-{sym.end_line})",
                    },
                    {
                        "type": "reference_scan",
                        "file": file_obj.path,
                        "symbol": sym.name,
                        "snippet": f"0 references found across {len(ctx.files)} project files.",
                    },
                ]

                findings.append(
                    CandidateFinding(
                        category=FindingCategory.UNUSED_CODE,
                        title=f"Potentially unreferenced symbol: `{sym.name}`",
                        description=(
                            f"The {sym.symbol_type.value.lower()} `{sym.name}` in `{file_obj.path}` appears to have "
                            f"no detected internal references in the indexed project."
                        ),
                        why_it_matters=(
                            "Unreferenced symbols may indicate obsolete dead code, incomplete refactorings, "
                            "or forgotten experimental implementations adding maintenance overhead."
                        ),
                        severity=FindingSeverity.LOW,
                        confidence=FindingConfidence.MEDIUM,
                        recommendation=(
                            f"Verify whether `{sym.name}` is called dynamically or externally. "
                            f"If obsolete, consider deprecating or safely removing it."
                        ),
                        evidence=evidence,
                        related_entities=[sym.name, file_obj.path],
                        metadata={
                            "symbol": sym.name,
                            "file": file_obj.path,
                            "kind": sym.symbol_type.value,
                        },
                        score=30.0,
                    )
                )

                # Cap findings to avoid spamming
                if len(findings) >= 8:
                    break

        return findings
