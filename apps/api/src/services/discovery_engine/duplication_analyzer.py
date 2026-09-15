import re
from difflib import SequenceMatcher
from typing import Any

from apps.api.src.models.enums import (
    FindingCategory,
    FindingConfidence,
    FindingSeverity,
)
from apps.api.src.services.discovery_engine.base import (
    CandidateFinding,
    DiscoveryAnalyzer,
    DiscoveryContext,
)


class DuplicationAnalyzer(DiscoveryAnalyzer):
    @property
    def category(self) -> FindingCategory:
        return FindingCategory.DUPLICATION

    async def analyze(self, ctx: DiscoveryContext) -> list[CandidateFinding]:
        findings: list[CandidateFinding] = []

        # 1. Filter non-test, non-generated symbols with meaningful body chunks
        candidate_chunks = [
            c
            for c in ctx.chunks
            if c.chunk_type.upper() in ("FUNCTION", "METHOD", "CLASS")
            and len(c.content.strip().splitlines()) >= 4
            and "test" not in c.path.lower()
            and "spec" not in c.path.lower()
            and "migration" not in c.path.lower()
        ]

        # Group by name similarity or function suffix (e.g. *validate*, *auth*, *hash*, *format*)
        pairs_compared: set[tuple[str, str]] = set()

        for i in range(len(candidate_chunks)):
            c1 = candidate_chunks[i]
            for j in range(i + 1, len(candidate_chunks)):
                c2 = candidate_chunks[j]

                # Don't compare symbols within same file
                if c1.path == c2.path:
                    continue

                pair_key = tuple(sorted([f"{c1.path}:{c1.name}", f"{c2.path}:{c2.name}"]))
                if pair_key in pairs_compared:
                    continue
                pairs_compared.add(pair_key)

                # Name similarity heuristic (e.g. validate_user vs validate_profile, or identical names)
                name1 = c1.name.lower()
                name2 = c2.name.lower()
                similar_names = (
                    name1 == name2
                    or (len(name1) > 4 and name1 in name2)
                    or (len(name2) > 4 and name2 in name1)
                )

                if not similar_names:
                    continue

                # Normalize code content for comparison (strip whitespace and comments)
                norm1 = self._normalize_code(c1.content)
                norm2 = self._normalize_code(c2.content)

                ratio = SequenceMatcher(None, norm1, norm2).ratio()

                if ratio >= 0.78:
                    evidence: list[dict[str, Any]] = [
                        {
                            "type": "duplicate_candidate",
                            "file": c1.path,
                            "symbol": c1.name,
                            "lines": f"{c1.start_line}-{c1.end_line}",
                            "snippet": c1.content[:200],
                        },
                        {
                            "type": "duplicate_candidate",
                            "file": c2.path,
                            "symbol": c2.name,
                            "lines": f"{c2.start_line}-{c2.end_line}",
                            "snippet": c2.content[:200],
                        },
                    ]

                    findings.append(
                        CandidateFinding(
                            category=FindingCategory.DUPLICATION,
                            title=f"Potential logic overlap: `{c1.name}` & `{c2.name}`",
                            description=(
                                f"The implementations of `{c1.name}` in `{c1.path}` and "
                                f"`{c2.name}` in `{c2.path}` contain substantial overlapping logic "
                                f"({int(ratio * 100)}% structural similarity)."
                            ),
                            why_it_matters=(
                                "Duplicated logic leads to divergent bug fixes, code bloat, and inconsistent "
                                "system behavior when one implementation is updated and the other forgotten."
                            ),
                            severity=FindingSeverity.MEDIUM,
                            confidence=FindingConfidence.HIGH
                            if ratio >= 0.88
                            else FindingConfidence.MEDIUM,
                            recommendation=(
                                "Consolidate common logic into a shared utility or base class to guarantee "
                                "consistent behavior across both usages."
                            ),
                            evidence=evidence,
                            related_entities=[c1.path, c2.path, c1.name, c2.name],
                            metadata={"similarity_ratio": ratio},
                            score=50.0 + (ratio * 20.0),
                        )
                    )

                    if len(findings) >= 5:
                        return findings

        return findings

    def _normalize_code(self, code: str) -> str:
        # Strip comments and extra spaces
        code = re.sub(r"#.*", "", code)
        code = re.sub(r"//.*", "", code)
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
        return " ".join(code.split())
