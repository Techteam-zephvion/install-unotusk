import re
from collections import defaultdict
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


class DocumentationGapAnalyzer(DiscoveryAnalyzer):
    @property
    def category(self) -> FindingCategory:
        return FindingCategory.DOCUMENTATION_GAP

    async def analyze(self, ctx: DiscoveryContext) -> list[CandidateFinding]:
        findings: list[CandidateFinding] = []

        # 1. Map inbound consumers for files
        consumers_by_file: dict[str, set[str]] = defaultdict(set)
        all_paths = set(ctx.file_by_path.keys())

        for src_file in ctx.files:
            deps = ctx.dependencies_by_file_id.get(src_file.id, [])
            for dep in deps:
                target_clean = ctx.get_target_for_dep(dep).strip("'\"")
                for path in all_paths:
                    if (
                        path == target_clean
                        or path.endswith(target_clean)
                        or target_clean.replace(".", "/") in path
                    ) and path != src_file.path:
                        consumers_by_file[path].add(src_file.path)

        # 2. Collect documentation chunks (e.g. README.md, docs)
        doc_texts = [
            chunk.content.lower()
            for chunk in ctx.chunks
            if "readme" in chunk.path.lower() or "doc" in chunk.path.lower()
        ]

        # 3. Check important symbols or files
        for sym in ctx.symbols:
            if sym.symbol_type not in (SymbolType.CLASS, SymbolType.INTERFACE):
                continue

            file_obj = ctx.file_by_id.get(sym.file_id)
            if not file_obj:
                continue

            # Skip test files
            if "test" in file_obj.path.lower() or "spec" in file_obj.path.lower():
                continue

            consumers = consumers_by_file.get(file_obj.path, set())
            # Important if >= 2 consumers
            if len(consumers) >= 2:
                # Check if symbol has docstring/comment in its chunk
                sym_chunk = next(
                    (c for c in ctx.chunks if c.path == file_obj.path and c.name == sym.name),
                    None,
                )

                has_docstring = False
                if sym_chunk and sym_chunk.content:
                    # Check for docstrings (""" or /**)
                    if (
                        '"""' in sym_chunk.content
                        or "/**" in sym_chunk.content
                        or "'''" in sym_chunk.content
                    ):
                        has_docstring = True

                # Check if mentioned in README/docs
                sym_name_lower = sym.name.lower()
                mentioned_in_docs = any(
                    re.search(r"\b" + re.escape(sym_name_lower) + r"\b", dt) for dt in doc_texts
                )

                if not has_docstring and not mentioned_in_docs:
                    evidence: list[dict[str, Any]] = [
                        {
                            "type": "undocumented_symbol",
                            "file": file_obj.path,
                            "symbol": sym.name,
                            "lines": f"{sym.start_line}-{sym.end_line}",
                            "snippet": f"{sym.name} has {len(consumers)} consumers but no docstrings.",
                        },
                        {
                            "type": "doc_search",
                            "file": file_obj.path,
                            "snippet": "No relevant documentation was found in the indexed project.",
                        },
                    ]

                    findings.append(
                        CandidateFinding(
                            category=FindingCategory.DOCUMENTATION_GAP,
                            title=f"Undocumented core component: `{sym.name}`",
                            description=(
                                f"The component `{sym.name}` in `{file_obj.path}` is utilized by "
                                f"{len(consumers)} consumers, but no docstrings or project documentation were detected."
                            ),
                            why_it_matters=(
                                "Key architectural abstractions without documentation increase onboarding friction, "
                                "misunderstandings of behavioral contracts, and bug rates."
                            ),
                            severity=FindingSeverity.MEDIUM
                            if len(consumers) >= 5
                            else FindingSeverity.LOW,
                            confidence=FindingConfidence.HIGH,
                            recommendation=(
                                f"Add clear docstrings and interface documentation describing `{sym.name}`'s "
                                f"responsibilities, parameters, and invariants."
                            ),
                            evidence=evidence,
                            related_entities=[sym.name, file_obj.path],
                            metadata={"consumers_count": len(consumers), "symbol": sym.name},
                            score=45.0,
                        )
                    )

                    if len(findings) >= 5:
                        break

        return findings
