from apps.api.src.models.enums import FindingSeverity
from apps.api.src.services.discovery_engine.base import CandidateFinding

SEVERITY_ORDER = {
    FindingSeverity.CRITICAL: 5,
    FindingSeverity.HIGH: 4,
    FindingSeverity.MEDIUM: 3,
    FindingSeverity.LOW: 2,
    FindingSeverity.INFO: 1,
}


def deduplicate_findings(findings: list[CandidateFinding]) -> list[CandidateFinding]:
    """Deduplicates candidate findings based on category and affected entities/files."""
    deduped: dict[str, CandidateFinding] = {}

    for finding in findings:
        # Build canonical fingerprint
        entities_sorted = sorted(finding.related_entities)
        fingerprint = f"{finding.category.value}:{':'.join(entities_sorted)}"

        if fingerprint not in deduped:
            deduped[fingerprint] = finding
        else:
            existing = deduped[fingerprint]
            # Keep higher severity finding
            if SEVERITY_ORDER.get(finding.severity, 0) > SEVERITY_ORDER.get(existing.severity, 0):
                deduped[fingerprint] = finding
            # If same severity, keep the one with higher score or more evidence
            elif len(finding.evidence) > len(existing.evidence):
                deduped[fingerprint] = finding

    return list(deduped.values())
