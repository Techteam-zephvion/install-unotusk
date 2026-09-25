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


class CouplingAnalyzer(DiscoveryAnalyzer):
    def __init__(self, high_threshold: int = 15, medium_threshold: int = 6):
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.COUPLING

    async def analyze(self, ctx: DiscoveryContext) -> list[CandidateFinding]:
        findings: list[CandidateFinding] = []

        # 1. Map consumers per file: file_path -> set of consuming file paths
        consumers_by_file: dict[str, set[str]] = defaultdict(set)
        for src_file in ctx.files:
            deps = ctx.dependencies_by_file_id.get(src_file.id, [])
            for dep in deps:
                resolved_target = ctx.resolve_dep_target_path(dep, src_file.path)
                if resolved_target and resolved_target != src_file.path:
                    consumers_by_file[resolved_target].add(src_file.path)

        # 2. Check for high-coupling hotspots
        for target_path, consumers in consumers_by_file.items():
            consumer_count = len(consumers)
            if consumer_count >= self.medium_threshold:
                severity = (
                    FindingSeverity.HIGH
                    if consumer_count >= self.high_threshold
                    else FindingSeverity.MEDIUM
                )

                sorted_consumers = sorted(list(consumers))
                evidence: list[dict[str, Any]] = [
                    {
                        "type": "file_metric",
                        "file": target_path,
                        "consumers_count": consumer_count,
                        "snippet": f"Depended upon by {consumer_count} distinct files.",
                    }
                ]
                for c in sorted_consumers[:10]:
                    evidence.append(
                        {
                            "type": "consumer_reference",
                            "file": c,
                            "target": target_path,
                            "snippet": f"{c} depends on {target_path}",
                        }
                    )

                findings.append(
                    CandidateFinding(
                        category=FindingCategory.COUPLING,
                        title=f"High coupling: `{target_path}` has {consumer_count} consumers",
                        description=(
                            f"The component `{target_path}` is directly imported by {consumer_count} distinct files. "
                            f"It represents a central hub in the repository's dependency graph."
                        ),
                        why_it_matters=(
                            "Modifications to this file have a large blast radius and can cascade breaking changes "
                            "across many downstream consumers. It requires high test vigilance."
                        ),
                        severity=severity,
                        confidence=FindingConfidence.HIGH,
                        recommendation=(
                            "Consider introducing stable, narrow interface contracts or splitting large monolithic "
                            "services into cohesive, smaller single-responsibility modules."
                        ),
                        evidence=evidence,
                        related_entities=[target_path] + sorted_consumers[:5],
                        metadata={"consumer_count": consumer_count},
                        score=80.0 if severity == FindingSeverity.HIGH else 60.0,
                    )
                )

        return findings
