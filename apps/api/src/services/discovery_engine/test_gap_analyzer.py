import os
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


class TestGapAnalyzer(DiscoveryAnalyzer):
    @property
    def category(self) -> FindingCategory:
        return FindingCategory.TEST_GAP

    async def analyze(self, ctx: DiscoveryContext) -> list[CandidateFinding]:
        findings: list[CandidateFinding] = []
        all_paths = set(ctx.file_by_path.keys())

        # Collect all test paths
        test_paths = {
            p.lower()
            for p in all_paths
            if "test" in p.lower() or "spec" in p.lower()
        }

        # Inspect core source files that define major classes or services
        for file_obj in ctx.files:
            path_lower = file_obj.path.lower()

            # Skip test files, docs, migrations, config
            if (
                "test" in path_lower
                or "spec" in path_lower
                or "alembic" in path_lower
                or "migration" in path_lower
                or path_lower.endswith((".json", ".md", ".yaml", ".yml", ".sql"))
                or "conftest" in path_lower
            ):
                continue

            # Check if file defines important classes or functions
            symbols = ctx.symbols_by_file_id.get(file_obj.id, [])
            has_major_symbols = any(
                s.symbol_type in (SymbolType.CLASS, SymbolType.FUNCTION) for s in symbols
            )
            if not has_major_symbols:
                continue

            # Derive expected test file patterns
            base_name = os.path.splitext(os.path.basename(file_obj.path))[0].lower()
            expected_test_patterns = [
                f"test_{base_name}",
                f"{base_name}_test",
                f"{base_name}.test",
                f"{base_name}.spec",
            ]

            has_test = any(
                any(pat in tp for pat in expected_test_patterns)
                for tp in test_paths
            )

            if not has_test:
                evidence: list[dict[str, Any]] = [
                    {
                        "type": "test_search",
                        "file": file_obj.path,
                        "symbols_count": len(symbols),
                        "snippet": "No corresponding test file was detected.",
                    }
                ]

                findings.append(
                    CandidateFinding(
                        category=FindingCategory.TEST_GAP,
                        title=f"Test gap detected: `{file_obj.path}` has no matching tests",
                        description=(
                            f"The source file `{file_obj.path}` defines {len(symbols)} symbols, "
                            f"but no corresponding test file was detected in the project test suite."
                        ),
                        why_it_matters=(
                            "Unchecked source modules risk regressions when modified. "
                            "Automated tests provide safety rails and document intended behavior."
                        ),
                        severity=FindingSeverity.MEDIUM if len(symbols) >= 3 else FindingSeverity.LOW,
                        confidence=FindingConfidence.HIGH,
                        recommendation=(
                            f"Create a test suite (e.g. `test_{base_name}.py` or `{base_name}.test.ts`) "
                            f"to validate core behaviors and edge cases."
                        ),
                        evidence=evidence,
                        related_entities=[file_obj.path] + [s.name for s in symbols[:3]],
                        metadata={"symbols_count": len(symbols), "file": file_obj.path},
                        score=35.0 if len(symbols) < 3 else 50.0,
                    )
                )

                if len(findings) >= 8:
                    break

        return findings
