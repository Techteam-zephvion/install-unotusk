import uuid
from datetime import UTC, datetime
from typing import Any

from apps.api.src.schemas.intelligence import (
    BDDScenarioItem,
    EvidenceItem,
    FeatureSpecificationResponse,
)


class FeatureSpecificationGenerator:
    """
    Approved Code Lane Feature-Specification Generation Engine.
    Consumes Code Lane assembled evidence with rich provenance and generates
    grounded feature specifications (BDD Gherkin scenarios, confirmed vs inferred
    constraints, and architectural contracts).
    """

    @classmethod
    def generate_from_evidence(
        cls,
        project_id: uuid.UUID,
        feature_request: str,
        evidence_items: list[EvidenceItem],
        debug_signals: dict[str, Any] | None = None,
        thinking_tier: str | None = "warm",
    ) -> FeatureSpecificationResponse:
        now = datetime.now(UTC)
        signals = dict(debug_signals or {})

        # 1. Handle empty / missing evidence safely (Zero-Hallucination Guardrail)
        if not evidence_items:
            return FeatureSpecificationResponse(
                project_id=project_id,
                feature_name=cls._extract_feature_name(feature_request),
                intent=feature_request,
                confidence="LOW",
                confirmed_code_facts=[],
                inferred_requirements=[
                    f"Design and implement new component for: '{feature_request}'",
                    "Establish unit and integration test coverage for the new feature",
                ],
                scenarios=[
                    BDDScenarioItem(
                        id=1,
                        title="Proposed Initial Implementation",
                        given="No existing implementation was found in the current codebase snapshot",
                        when="The requested feature is invoked",
                        then="The system shall execute new functionality adhering to project standards",
                        cited_files=[],
                        cited_symbols=[],
                    )
                ],
                evidence=[],
                cited_files=[],
                cited_symbols=[],
                has_superseded_precursors=False,
                warning="No matching implementation found in current codebase snapshot. Specification is speculative/unanchored.",
                debug_signals=signals,
                created_at=now,
            )

        # 2. Partition current vs superseded / deleted evidence
        current_evidence: list[EvidenceItem] = []
        superseded_evidence: list[EvidenceItem] = []

        for e in evidence_items:
            if e.is_superseded or e.is_deleted:
                superseded_evidence.append(e)
            else:
                current_evidence.append(e)

        has_superseded = len(superseded_evidence) > 0

        # 2b. If all evidence is superseded or deleted, do NOT represent as current active code
        if not current_evidence and superseded_evidence:
            historical_facts: list[str] = []
            for e in superseded_evidence:
                sym_str = f" symbol '{e.symbol}'" if e.symbol else ""
                lines_str = f" (lines {e.lines})" if e.lines else ""
                tag = "deleted" if e.is_deleted else "superseded"
                by_str = f" by commit {e.superseded_by_sha[:8]}" if e.superseded_by_sha else ""
                stmt = f"Historical precursor ({tag}{by_str}):{sym_str} in '{e.file}'{lines_str}"
                if stmt not in historical_facts:
                    historical_facts.append(stmt)

            cited_files = sorted(list({e.file for e in superseded_evidence if e.file}))
            cited_symbols = sorted(list({e.symbol for e in superseded_evidence if e.symbol}))
            primary_file = cited_files[0] if cited_files else "src/main.py"
            primary_symbol = cited_symbols[0] if cited_symbols else "Precursor"

            max_hist_rel = max((e.relevance for e in superseded_evidence), default=0.0)
            confidence = "LOW" if max_hist_rel < 0.5 else "MEDIUM"

            return FeatureSpecificationResponse(
                project_id=project_id,
                feature_name=cls._extract_feature_name(feature_request),
                intent=feature_request,
                confidence=confidence,
                confirmed_code_facts=historical_facts[:8],
                inferred_requirements=[
                    f"Design replacement for superseded/historical precursor: '{feature_request}'",
                    f"Implement new component replacing deprecated logic in '{primary_file}'",
                    "Establish migration path and test suite verifying deprecation retirement",
                ],
                scenarios=[
                    BDDScenarioItem(
                        id=1,
                        title=f"Replacement: {cls._extract_feature_name(feature_request)}",
                        given=f"Historical precursor '{primary_symbol}' in '{primary_file}' was superseded or deprecated",
                        when=f"A client executes the replacement feature for '{feature_request}'",
                        then=f"The system executes the new implementation without executing deprecated code in '{primary_file}'",
                        cited_files=[primary_file],
                        cited_symbols=[primary_symbol] if cited_symbols else [],
                    ),
                    BDDScenarioItem(
                        id=2,
                        title="Legacy Boundary & Deprecation Rejection",
                        given=f"A client targeting superseded interfaces from '{primary_file}'",
                        when="A request using deprecated parameters or endpoints is received",
                        then="The system rejects or redirects the request to the new active implementation with clear guidance",
                        cited_files=cited_files[:2],
                        cited_symbols=cited_symbols[:2],
                    ),
                ],
                evidence=evidence_items,
                cited_files=cited_files,
                cited_symbols=cited_symbols,
                has_superseded_precursors=True,
                warning=f"Notice: All {len(superseded_evidence)} retrieved code item(s) represent historical or superseded precursors. No active current code was found; new implementation is required.",
                debug_signals=signals,
                created_at=now,
            )

        # Primary evidence pool for grounding is current active code
        grounding_pool = current_evidence

        # 3. Extract verified code facts (strictly from current evidence)
        confirmed_facts: list[str] = []
        for e in grounding_pool:
            if e.atomic_code_facts:
                for fact in e.atomic_code_facts:
                    if isinstance(fact, dict) and "statement" in fact:
                        stmt = str(fact["statement"]).strip()
                        if stmt and stmt not in confirmed_facts:
                            confirmed_facts.append(stmt)
                    elif isinstance(fact, str) and fact.strip() and fact.strip() not in confirmed_facts:
                        confirmed_facts.append(fact.strip())
            else:
                sym_str = f" symbol '{e.symbol}'" if e.symbol else ""
                lines_str = f" (lines {e.lines})" if e.lines else ""
                file_str = e.file if e.file else "unknown"
                statement = f"Confirmed existing{sym_str} in '{file_str}'{lines_str}"
                if statement not in confirmed_facts:
                    confirmed_facts.append(statement)

            # Record relationship path if verified
            if e.relationship_path:
                rel_stmt = f"Structural relationship: {e.relationship_path}"
                if rel_stmt not in confirmed_facts:
                    confirmed_facts.append(rel_stmt)

        # 4. Extract cited files and symbols
        cited_files = sorted(list({e.file for e in grounding_pool if e.file}))
        cited_symbols = sorted(list({e.symbol for e in grounding_pool if e.symbol}))

        # 5. Formulate inferred requirements for requested feature
        inferred_reqs = [
            f"Implement requested capability: '{feature_request}'",
            f"Integrate changes with existing components: {', '.join(cited_symbols[:3]) if cited_symbols else ', '.join(cited_files[:2])}",
            "Preserve backwards-compatibility for existing API consumers and client contracts",
        ]

        # 6. Generate BDD Given/When/Then Scenarios grounded in actual files/symbols
        primary_file = cited_files[0] if cited_files else "src/main.py"
        primary_symbol = cited_symbols[0] if cited_symbols else "Handler"

        # Multi-file integration scenario when multiple files are cited
        if len(cited_files) >= 2:
            multi_file_scenario = BDDScenarioItem(
                id=2,
                title="Multi-Component Integration & Boundary Contract",
                given=f"Components '{cited_files[0]}' and '{cited_files[1]}' configured with active bindings",
                when=f"The requested operation for '{feature_request}' traverses component boundaries",
                then=f"Both '{cited_files[0]}' and '{cited_files[1]}' maintain transaction consistency and return coordinated responses",
                cited_files=cited_files[:2],
                cited_symbols=cited_symbols[:2],
            )
        else:
            multi_file_scenario = BDDScenarioItem(
                id=2,
                title="Input Validation & Rate Boundary",
                given=f"The service configured per '{primary_file}' with active constraints",
                when="A client supplies invalid parameters or exceeds permissible rate limits",
                then="The request is rejected with a structured client error before mutating state",
                cited_files=cited_files[:2],
                cited_symbols=cited_symbols[:2],
            )

        scenarios: list[BDDScenarioItem] = [
            BDDScenarioItem(
                id=1,
                title=f"Happy Path: {cls._extract_feature_name(feature_request)}",
                given=f"A client making requests targeting '{primary_symbol}' in '{primary_file}'",
                when=f"The client executes the action for '{feature_request}' with valid parameters",
                then=f"The operation completes successfully and returns the expected result conforming to '{primary_file}'",
                cited_files=[primary_file],
                cited_symbols=[primary_symbol] if cited_symbols else [],
            ),
            multi_file_scenario,
            BDDScenarioItem(
                id=3,
                title="Error Resilience & State Preservation",
                given="An active downstream dependency or storage transaction under load",
                when="A transient failure or timeout occurs during feature execution",
                then="The system logs diagnostic telemetry, rolls back partial mutations, and raises a controlled error",
                cited_files=cited_files[:3],
                cited_symbols=cited_symbols[:3],
            ),
        ]

        # 7. Determine confidence based on highest relevance score
        max_relevance = max((e.relevance for e in grounding_pool), default=0.0)
        if max_relevance >= 0.8:
            confidence = "HIGH"
        elif max_relevance >= 0.5:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        # 8. Set diagnostic warning if historical code or low relevance was present
        warning_msg: str | None = None
        if has_superseded:
            warning_msg = (
                f"Notice: {len(superseded_evidence)} superseded or historical code item(s) detected. "
                f"Specification is grounded exclusively in current active code ({len(current_evidence)} item(s))."
            )
        elif max_relevance < 0.4:
            warning_msg = "Weak code evidence detected. Specification requirements are primarily inferred."

        return FeatureSpecificationResponse(
            project_id=project_id,
            feature_name=cls._extract_feature_name(feature_request),
            intent=feature_request,
            confidence=confidence,
            confirmed_code_facts=confirmed_facts[:8],
            inferred_requirements=inferred_reqs,
            scenarios=scenarios,
            evidence=evidence_items,
            cited_files=cited_files,
            cited_symbols=cited_symbols,
            has_superseded_precursors=has_superseded,
            warning=warning_msg,
            debug_signals=signals,
            created_at=now,
        )

    @staticmethod
    def _extract_feature_name(request: str) -> str:
        words = request.strip().split()
        if not words:
            return "Feature Specification"
        clean_words = [w for w in words[:6] if w.lower() not in ("generate", "a", "an", "the", "spec", "bdd", "for")]
        if not clean_words:
            clean_words = words[:4]
        return " ".join(clean_words).title()
