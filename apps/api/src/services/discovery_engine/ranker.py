from apps.api.src.models.enums import FindingConfidence, FindingSeverity
from apps.api.src.services.discovery_engine.base import CandidateFinding

SEVERITY_WEIGHTS = {
    FindingSeverity.CRITICAL: 100.0,
    FindingSeverity.HIGH: 75.0,
    FindingSeverity.MEDIUM: 50.0,
    FindingSeverity.LOW: 25.0,
    FindingSeverity.INFO: 10.0,
}

CONFIDENCE_WEIGHTS = {
    FindingConfidence.HIGH: 1.0,
    FindingConfidence.MEDIUM: 0.8,
    FindingConfidence.LOW: 0.6,
}


def rank_findings(findings: list[CandidateFinding]) -> list[CandidateFinding]:
    """Calculates deterministic scores and sorts findings by priority."""
    for finding in findings:
        sev_base = SEVERITY_WEIGHTS.get(finding.severity, 25.0)
        conf_mult = CONFIDENCE_WEIGHTS.get(finding.confidence, 0.8)
        entity_impact = min(len(finding.related_entities) * 2.5, 15.0)

        finding.score = round((sev_base * conf_mult) + entity_impact, 2)

    return sorted(findings, key=lambda f: f.score, reverse=True)
