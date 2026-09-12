from collections import defaultdict
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


class ChangeRiskAnalyzer(DiscoveryAnalyzer):
    @property
    def category(self) -> FindingCategory:
        return FindingCategory.CHANGE_RISK

    async def analyze(self, ctx: DiscoveryContext) -> list[CandidateFinding]:
        findings: list[CandidateFinding] = []

        # 1. Map inbound consumers
        inbound_counts: dict[str, set[str]] = defaultdict(set)
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
                        inbound_counts[path].add(src_file.path)

        # 2. Evaluate each file for composite risk (inbound + outbound + symbol density)
        for f in ctx.files:
            in_consumers = len(inbound_counts.get(f.path, set()))
            out_deps = len(ctx.dependencies_by_file_id.get(f.id, []))
            syms = len(ctx.symbols_by_file_id.get(f.id, []))

            # Composite threshold:
            # Component is central (consumers >= 4) AND structurally complex (out_deps >= 3 or syms >= 5)
            if in_consumers >= 4 and (out_deps >= 3 or syms >= 5):
                severity = (
                    FindingSeverity.HIGH
                    if in_consumers >= 8 or (out_deps >= 6 and syms >= 8)
                    else FindingSeverity.MEDIUM
                )

                evidence: list[dict[str, Any]] = [
                    {
                        "type": "risk_metrics",
                        "file": f.path,
                        "consumers": in_consumers,
                        "outbound_dependencies": out_deps,
                        "symbols_count": syms,
                        "snippet": (
                            f"{in_consumers} downstream consumers, {out_deps} outbound dependencies, "
                            f"{syms} declared symbols."
                        ),
                    }
                ]

                findings.append(
                    CandidateFinding(
                        category=FindingCategory.CHANGE_RISK,
                        title=f"Potential change-risk hotspot: `{f.path}`",
                        description=(
                            f"The component `{f.path}` combines heavy downstream consumption ({in_consumers} consumers) "
                            f"with internal structural complexity ({out_deps} dependencies, {syms} symbols)."
                        ),
                        why_it_matters=(
                            "Changes to high-impact components with large fan-in and fan-out have high blast radius. "
                            "Refactorings here risk ripple effects across the system."
                        ),
                        severity=severity,
                        confidence=FindingConfidence.HIGH,
                        recommendation=(
                            "Ensure comprehensive automated unit and integration tests cover this component. "
                            "Decouple responsibilities to reduce outbound dependencies."
                        ),
                        evidence=evidence,
                        related_entities=[f.path],
                        metadata={
                            "consumers": in_consumers,
                            "dependencies": out_deps,
                            "symbols": syms,
                        },
                        score=75.0 if severity == FindingSeverity.HIGH else 55.0,
                    )
                )

        return findings
