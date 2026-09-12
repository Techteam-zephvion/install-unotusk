import re
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

LEGACY_NAME_INDICATORS = ["legacy", "deprecated", "_old", "old_", "v1_"]


class LegacyAnalyzer(DiscoveryAnalyzer):
    @property
    def category(self) -> FindingCategory:
        return FindingCategory.LEGACY

    async def analyze(self, ctx: DiscoveryContext) -> list[CandidateFinding]:
        findings: list[CandidateFinding] = []
        all_paths = set(ctx.file_by_path.keys())

        for file_obj in ctx.files:
            path_lower = file_obj.path.lower()
            if "test" in path_lower or "spec" in path_lower:
                continue

            signals: list[str] = []

            # Signal 1: Name indicates legacy / deprecated
            matching_indicator = next((ind for ind in LEGACY_NAME_INDICATORS if ind in path_lower), None)
            if matching_indicator:
                signals.append(f"Filename contains legacy indicator '{matching_indicator}'")

            # Signal 2: Deprecated decorator or comments in file chunks
            file_chunks = [c for c in ctx.chunks if c.path == file_obj.path]
            has_depr_comment = any(
                re.search(r"@deprecated|#\s*deprecated|/\*\s*deprecated", c.content, re.IGNORECASE)
                for c in file_chunks
            )
            if has_depr_comment:
                signals.append("Source code contains explicit `@deprecated` comment or decorator")

            # Signal 3: Coexistence with clean non-legacy sibling
            # e.g. src/auth_legacy.py while src/auth.py or src/auth/service.py exists
            clean_name = path_lower
            for ind in LEGACY_NAME_INDICATORS:
                clean_name = clean_name.replace(ind, "")
            sibling_exists = any(p.lower() == clean_name for p in all_paths if p != file_obj.path)
            if sibling_exists:
                signals.append(f"A modern alternative sibling file exists at '{clean_name}'")

            # Require at least 2 distinct signals
            if len(signals) >= 2:
                evidence: list[dict[str, Any]] = [
                    {
                        "type": "legacy_signals",
                        "file": file_obj.path,
                        "signals": signals,
                        "snippet": " | ".join(signals),
                    }
                ]

                findings.append(
                    CandidateFinding(
                        category=FindingCategory.LEGACY,
                        title=f"Potential legacy component: `{file_obj.path}`",
                        description=(
                            f"Multiple signals indicate that `{file_obj.path}` is a legacy or deprecated component: "
                            f"{', '.join(signals)}."
                        ),
                        why_it_matters=(
                            "Leaving deprecated legacy code in the codebase creates confusion for new engineers, "
                            "drags down indexing performance, and risks unintended invocation."
                        ),
                        severity=FindingSeverity.MEDIUM,
                        confidence=FindingConfidence.HIGH,
                        recommendation=(
                            f"Audit all active dependencies on `{file_obj.path}`. "
                            f"Migrate any remaining callers to modern replacements and schedule deletion."
                        ),
                        evidence=evidence,
                        related_entities=[file_obj.path],
                        metadata={"signals": signals},
                        score=50.0,
                    )
                )

        return findings
