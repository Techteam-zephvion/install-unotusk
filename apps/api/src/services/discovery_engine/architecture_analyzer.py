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


class ArchitectureAnalyzer(DiscoveryAnalyzer):
    @property
    def category(self) -> FindingCategory:
        return FindingCategory.ARCHITECTURE

    async def analyze(self, ctx: DiscoveryContext) -> list[CandidateFinding]:
        findings: list[CandidateFinding] = []

        for src_file in ctx.files:
            src_path_lower = src_file.path.lower()
            is_test_file = (
                "test" in src_path_lower
                or "spec" in src_path_lower
                or "conftest" in src_path_lower
            )

            deps = ctx.dependencies_by_file_id.get(src_file.id, [])

            for dep in deps:
                raw_target = ctx.get_target_for_dep(dep)
                target_clean = raw_target.strip("'\"").lower()

                # Rule 1: Production code importing test code/fixtures
                if not is_test_file:
                    if (
                        target_clean.startswith("tests")
                        or target_clean.startswith("test")
                        or "/tests/" in target_clean
                        or "/test/" in target_clean
                        or "conftest" in target_clean
                    ):
                        evidence: list[dict[str, Any]] = [
                            {
                                "type": "boundary_violation",
                                "file": src_file.path,
                                "target": raw_target,
                                "lines": f"{dep.line_number}" if dep.line_number else "N/A",
                                "snippet": f"{src_file.path} imports test code from {raw_target}",
                            }
                        ]

                        findings.append(
                            CandidateFinding(
                                category=FindingCategory.ARCHITECTURE,
                                title="Architectural violation: production file imports test code",
                                description=(
                                    f"Production file `{src_file.path}` imports from test package `{dep.target}`. "
                                    f"Production code should never depend on test harnesses or test fixtures."
                                ),
                                why_it_matters=(
                                    "Importing test code into production bundles test dependencies into release builds, "
                                    "creates accidental coupling to test fixtures, and can cause runtime deployment failures."
                                ),
                                severity=FindingSeverity.HIGH,
                                confidence=FindingConfidence.HIGH,
                                recommendation=(
                                    f"Move shared helpers out of `{dep.target}` into a shared production utility, "
                                    f"or refactor `{src_file.path}` to decouple it from test code."
                                ),
                                evidence=evidence,
                                related_entities=[src_file.path, dep.target],
                                metadata={"source": src_file.path, "target": dep.target},
                                score=80.0,
                            )
                        )

                # Rule 2: Web frontend directly importing backend database/ORM modules
                if "web/" in src_path_lower or "app/" in src_path_lower or "frontend/" in src_path_lower:
                    if (
                        "sqlalchemy" in target_clean
                        or "asyncpg" in target_clean
                        or "prisma" in target_clean
                        or "database" in target_clean
                    ):
                        evidence_web: list[dict[str, Any]] = [
                            {
                                "type": "boundary_violation",
                                "file": src_file.path,
                                "target": dep.target,
                                "lines": f"{dep.line_number}" if dep.line_number else "N/A",
                                "snippet": f"Client code in {src_file.path} imports {dep.target}",
                            }
                        ]

                        findings.append(
                            CandidateFinding(
                                category=FindingCategory.ARCHITECTURE,
                                title="Layer boundary breach: client code imports database layer",
                                description=(
                                    f"Frontend/client component `{src_file.path}` imports backend database "
                                    f"dependency `{dep.target}` directly."
                                ),
                                why_it_matters=(
                                    "Direct database access from presentation tiers violates separation of concerns, "
                                    "exposes database connection strings or credentials, and breaks modularity."
                                ),
                                severity=FindingSeverity.HIGH,
                                confidence=FindingConfidence.HIGH,
                                recommendation=(
                                    "Access database resources exclusively through authenticated backend API endpoints."
                                ),
                                evidence=evidence_web,
                                related_entities=[src_file.path, dep.target],
                                metadata={"source": src_file.path, "target": dep.target},
                                score=85.0,
                            )
                        )

        return findings
