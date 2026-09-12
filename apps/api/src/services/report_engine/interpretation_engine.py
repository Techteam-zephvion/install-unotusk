from collections import defaultdict
from typing import Any

from apps.api.src.models.enums import FindingCategory, FindingSeverity, KnowledgeClass
from apps.api.src.schemas.report import (
    ClaimItem,
    EvidenceRef,
    ExecutiveSummary,
    ImportantDependency,
    NextAction,
    ProjectUnderstanding,
    ReportDocument,
    RiskArea,
    TechnicalDebtItem,
    TestingAndDocs,
    TopDiscoveryItem,
    VitalMetrics,
)
from apps.api.src.services.report_engine.base import FactData


class InterpretationEngine:
    @classmethod
    def build_report_document(cls, facts: FactData) -> ReportDocument:
        # 1. Compute Vital Metrics & Assessment
        critical_count = sum(1 for f in facts.findings if f.severity == FindingSeverity.CRITICAL)
        high_count = sum(1 for f in facts.findings if f.severity == FindingSeverity.HIGH)
        medium_count = sum(1 for f in facts.findings if f.severity == FindingSeverity.MEDIUM)

        if critical_count >= 1 or high_count >= 4:
            state_assessment = "Elevated Risk — Critical structural cycles or high-coupling hotspots detected"
        elif high_count >= 1 or medium_count >= 3 or len(facts.findings) >= 5:
            state_assessment = "Moderate Risk — Structural coupling, documentation gaps, or test gaps detected"
        else:
            state_assessment = "Low Risk — Codebase demonstrates modular boundaries with low architectural friction"

        vital_metrics = VitalMetrics(
            total_files=len(facts.files),
            total_symbols=len(facts.symbols),
            total_dependencies=len(facts.dependencies),
            total_discoveries=len(facts.findings),
            critical_findings=critical_count,
            high_findings=high_count,
        )

        # Primary language summary
        primary_lang = "multi-language"
        if facts.language_counts:
            primary_lang = max(facts.language_counts.items(), key=lambda x: x[1])[0].capitalize()

        # 2. Major Areas (Directories)
        area_files: dict[str, list[str]] = defaultdict(list)
        for f in facts.files:
            parts = f.path.strip("/").split("/")
            if len(parts) > 1:
                # Group by top-level or second-level folder if src/
                prefix = parts[0]
                if prefix in ("src", "apps", "packages", "services") and len(parts) > 2:
                    prefix = f"{parts[0]}/{parts[1]}"
                area_files[prefix].append(f.path)
            else:
                area_files["root"].append(f.path)

        major_areas: list[dict[str, Any]] = []
        for prefix, paths in sorted(area_files.items(), key=lambda x: len(x[1]), reverse=True)[:6]:
            major_areas.append({
                "area": prefix,
                "files_count": len(paths),
                "sample_files": paths[:3],
            })

        # 3. Key Symbols (Sorted by consumer count)
        key_symbols_sorted = sorted(
            facts.symbols,
            key=lambda s: facts.symbol_consumers.get(s.name, 0),
            reverse=True,
        )
        key_symbols: list[dict[str, Any]] = []
        for s in key_symbols_sorted[:6]:
            c_count = facts.symbol_consumers.get(s.name, 0)
            sym_file_path = (
                facts.file_by_id[s.file_id].path
                if s.file_id in facts.file_by_id
                else (getattr(s, "file_path", "") or "")
            )
            key_symbols.append({
                "name": s.name,
                "symbol_type": s.symbol_type.value if hasattr(s.symbol_type, "value") else str(s.symbol_type),
                "file_path": sym_file_path,
                "consumer_count": c_count,
            })

        # 4. Project Understanding Section
        area_names = [a["area"] for a in major_areas if a["area"] != "root"]
        layers_desc = ", ".join(area_names) if area_names else "flat module structure"

        project_summary = (
            f"{facts.project.name} is a {primary_lang} project comprising "
            f"{len(facts.files):,} files and {len(facts.symbols):,} extracted AST symbols across {layers_desc}."
        )

        business_purpose_note = (
            f"Repository evidence establishes a {primary_lang} software project with {layers_desc}. "
            "Insufficient evidence in source comments to establish specific business domain beyond repository contents."
        )

        boundaries: list[str] = []
        if any("api" in a for a in area_names) and any("service" in a for a in area_names):
            boundaries.append("API presentation layer connects to service business logic.")
        if any("service" in a for a in area_names) and any("model" in a or "db" in a for a in area_names):
            boundaries.append("Services encapsulate persistence interactions with models/database.")
        if not boundaries:
            boundaries.append("Standard modular organization with internal and external package imports.")

        understanding = ProjectUnderstanding(
            primary_languages=facts.language_counts,
            repository_size={
                "total_lines": facts.total_lines,
                "total_bytes": facts.total_bytes,
                "size_formatted": f"{(facts.total_bytes / 1024):.1f} KB" if facts.total_bytes < 1048576 else f"{(facts.total_bytes / 1048576):.2f} MB",
            },
            major_areas=major_areas,
            key_symbols=key_symbols,
            architectural_boundaries=boundaries,
            business_purpose_note=business_purpose_note,
        )

        # 5. What Unotusk Observed (Concrete Facts)
        observed_items: list[ClaimItem] = []

        # Central symbols
        for ks in key_symbols:
            if ks["consumer_count"] >= 3:
                observed_items.append(ClaimItem(
                    claim_type=KnowledgeClass.OBSERVED,
                    title=f"High Coupling around {ks['name']}",
                    statement=f"{ks['name']} in {ks['file_path']} has {ks['consumer_count']} downstream consumer components.",
                    evidence=[EvidenceRef(
                        type="SYMBOL",
                        file=ks["file_path"],
                        symbol=ks["name"],
                        reference_type="DEPENDENCY",
                        consumers_count=ks["consumer_count"],
                    )],
                ))

        # Circular dependencies
        for cycle in facts.cycles:
            cycle_str = " → ".join(cycle)
            observed_items.append(ClaimItem(
                claim_type=KnowledgeClass.OBSERVED,
                title="Circular Dependency Cycle",
                statement=f"Circular dependency cycle detected across {len(cycle)} components: {cycle_str}.",
                evidence=[EvidenceRef(
                    type="CYCLE",
                    file=cycle[0] if cycle else None,
                    snippet=cycle_str,
                    reference_type="CIRCULAR_DEPENDENCY",
                )],
            ))

        # Findings-backed observations
        for f in facts.findings:
            if f.category in (FindingCategory.ARCHITECTURE, FindingCategory.TEST_GAP, FindingCategory.DOCUMENTATION_GAP):
                ev_refs = [
                    EvidenceRef(
                        type=e.get("type", "CODE"),
                        file=e.get("file"),
                        symbol=e.get("symbol"),
                        lines=str(e.get("lines")) if e.get("lines") else None,
                        snippet=e.get("snippet"),
                    )
                    for e in f.evidence[:2]
                ]
                observed_items.append(ClaimItem(
                    claim_type=KnowledgeClass.OBSERVED,
                    title=f.title,
                    statement=f.description,
                    evidence=ev_refs,
                ))

        # 6. Top Discoveries (ranked by severity)
        severity_order = {
            FindingSeverity.CRITICAL: 0,
            FindingSeverity.HIGH: 1,
            FindingSeverity.MEDIUM: 2,
            FindingSeverity.LOW: 3,
            FindingSeverity.INFO: 4,
            "CRITICAL": 0,
            "HIGH": 1,
            "MEDIUM": 2,
            "LOW": 3,
            "INFO": 4,
        }
        sorted_findings = sorted(facts.findings, key=lambda f: severity_order.get(f.severity, 99))
        top_discoveries: list[TopDiscoveryItem] = []
        for f in sorted_findings[:8]:
            top_discoveries.append(TopDiscoveryItem(
                finding_id=str(f.id),
                title=f.title,
                category=f.category.value if hasattr(f.category, "value") else str(f.category),
                severity=f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                confidence=f.confidence.value if hasattr(f.confidence, "value") else str(f.confidence),
                what_we_found=f.description,
                why_it_matters=f.why_it_matters,
                recommendation=f.recommendation,
                evidence=f.evidence,
            ))

        # 7. Risk Areas
        risk_areas_map: dict[str, list[ClaimItem]] = defaultdict(list)
        for f in facts.findings:
            cat_str = f.category.value if hasattr(f.category, "value") else str(f.category)
            ev_refs = [
                EvidenceRef(
                    type=e.get("type", "CODE"),
                    file=e.get("file"),
                    symbol=e.get("symbol"),
                    lines=str(e.get("lines")) if e.get("lines") else None,
                    snippet=e.get("snippet"),
                )
                for e in f.evidence[:2]
            ]
            risk_areas_map[cat_str].append(ClaimItem(
                claim_type=KnowledgeClass.OBSERVED,
                title=f.title,
                statement=f.description,
                evidence=ev_refs,
            ))

        risk_areas: list[RiskArea] = []
        risk_guidance = {
            "CIRCULAR_DEPENDENCY": (
                "Circular dependencies couple modules tightly, making independent testing difficult and increasing risk of initialization errors.",
                "Decouple the cycle by extracting shared types or contracts into an independent foundation module.",
            ),
            "COUPLING": (
                "High fan-in components amplify the blast radius of any signature or behavior change across the project.",
                "Review component boundaries and consider splitting into smaller, focused domain contracts.",
            ),
            "CHANGE_RISK": (
                "Components combining high fan-in with complex internal dependencies present high propagation risk during modification.",
                "Introduce rigorous regression testing and isolate critical interfaces before refactoring.",
            ),
            "TEST_GAP": (
                "Core domain modules lacking tests carry high risk of silent regressions during feature updates.",
                "Add targeted unit and integration tests covering the public interfaces of untested domain modules.",
            ),
            "DOCUMENTATION_GAP": (
                "High-impact interfaces without documentation increase onboarding friction and risk of misuse.",
                "Add clear docstrings documenting parameters, return values, and failure modes on public APIs.",
            ),
            "ARCHITECTURE": (
                "Layering violations weaken architectural encapsulation and complicate maintenance.",
                "Enforce strict dependency boundaries between presentation, business logic, and persistence.",
            ),
            "DUPLICATION": (
                "Duplicated logic leads to divergent bug fixes and inconsistent system behavior over time.",
                "Extract common logic into reusable utility functions or shared domain helpers.",
            ),
            "LEGACY": (
                "Deprecated or superseded patterns incur ongoing cognitive overhead and potential performance penalties.",
                "Plan phased migration away from legacy components toward active modern counterparts.",
            ),
        }

        for area, obs_list in risk_areas_map.items():
            derived_txt, rec_txt = risk_guidance.get(
                area,
                ("Identified patterns may introduce architectural friction or maintenance overhead.",
                 "Review discovered findings and align with engineering best practices.")
            )
            risk_areas.append(RiskArea(
                area=area.replace("_", " ").title(),
                observed=obs_list[:4],
                derived=derived_txt,
                recommended=rec_txt,
            ))

        # 8. Technical Debt Signals
        tech_debt: list[TechnicalDebtItem] = []
        for f in facts.findings:
            if f.category in (
                FindingCategory.DUPLICATION,
                FindingCategory.LEGACY,
                FindingCategory.DOCUMENTATION_GAP,
                FindingCategory.UNUSED_CODE,
                FindingCategory.CIRCULAR_DEPENDENCY,
            ):
                prio = "HIGH" if f.severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH) else "MEDIUM"
                tech_debt.append(TechnicalDebtItem(
                    signal=f.title,
                    evidence=f.evidence[:2],
                    impact=f.why_it_matters,
                    priority=prio,
                ))

        # 9. Important Dependencies
        important_deps: list[ImportantDependency] = []
        # Top consumer components
        for target_path, consumers in sorted(facts.file_consumers.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
            if len(consumers) >= 2:
                important_deps.append(ImportantDependency(
                    source=", ".join(list(consumers)[:3]) + (f" (+{len(consumers)-3} more)" if len(consumers) > 3 else ""),
                    target=target_path,
                    dependency_type="IMPORT",
                    consumer_count=len(consumers),
                    why_it_matters=f"{len(consumers)} internal modules depend on this component, making it a critical central hub.",
                ))
        # External packages
        for pkg in sorted(facts.external_packages)[:5]:
            important_deps.append(ImportantDependency(
                source="Project Modules",
                target=pkg,
                dependency_type="EXTERNAL_PACKAGE",
                consumer_count=1,
                why_it_matters="External library dependency required by project runtime.",
            ))

        # 10. Testing & Documentation State
        test_gap_findings = [f for f in facts.findings if f.category == FindingCategory.TEST_GAP]
        test_observed: list[ClaimItem] = []
        for tg in test_gap_findings[:3]:
            test_observed.append(ClaimItem(
                claim_type=KnowledgeClass.OBSERVED,
                title=tg.title,
                statement=tg.description,
                evidence=[EvidenceRef(
                    type=e.get("type", "FILE"),
                    file=e.get("file"),
                    lines=str(e.get("lines")) if e.get("lines") else None,
                ) for e in tg.evidence[:2]],
            ))

        doc_gap_findings = [f for f in facts.findings if f.category == FindingCategory.DOCUMENTATION_GAP]
        doc_observed: list[ClaimItem] = []
        for dg in doc_gap_findings[:3]:
            doc_observed.append(ClaimItem(
                claim_type=KnowledgeClass.OBSERVED,
                title=dg.title,
                statement=dg.description,
                evidence=[EvidenceRef(
                    type=e.get("type", "SYMBOL"),
                    file=e.get("file"),
                    symbol=e.get("symbol"),
                    lines=str(e.get("lines")) if e.get("lines") else None,
                ) for e in dg.evidence[:2]],
            ))

        testing_and_docs = TestingAndDocs(
            testing_observed=test_observed,
            testing_derived="Domain modules without corresponding test suites carry higher regression risk during changes.",
            testing_recommended="Implement test suites covering critical paths in untested domain modules.",
            testing_coverage_note="Test coverage percentage could not be established from repository data.",
            docs_observed=doc_observed,
            docs_recommended="Document public functions and central service interfaces with standard docstrings.",
        )

        # 11. Next Actions (Prioritized)
        next_actions: list[NextAction] = []
        action_idx = 1

        # Priority 1: Circular dependencies & Critical findings
        for f in facts.findings:
            if f.severity == FindingSeverity.CRITICAL or f.category == FindingCategory.CIRCULAR_DEPENDENCY:
                next_actions.append(NextAction(
                    id=f"action-{action_idx:02d}",
                    priority="HIGH",
                    title=f"Remediate: {f.title}",
                    description=f.recommendation,
                    claim_type=KnowledgeClass.RECOMMENDED,
                    related_finding_ids=[str(f.id)],
                    evidence=f.evidence[:2],
                ))
                action_idx += 1
                if action_idx > 3:
                    break

        # Priority 2: High coupling or change risks
        if len(next_actions) < 5:
            for f in facts.findings:
                if f.severity == FindingSeverity.HIGH and str(f.id) not in [a.related_finding_ids[0] for a in next_actions if a.related_finding_ids]:
                    next_actions.append(NextAction(
                        id=f"action-{action_idx:02d}",
                        priority="HIGH",
                        title=f"Review: {f.title}",
                        description=f.recommendation,
                        claim_type=KnowledgeClass.RECOMMENDED,
                        related_finding_ids=[str(f.id)],
                        evidence=f.evidence[:2],
                    ))
                    action_idx += 1
                    if len(next_actions) >= 4:
                        break

        # Priority 3: Test gaps & Doc gaps
        if len(next_actions) < 6:
            for f in facts.findings:
                if f.category in (FindingCategory.TEST_GAP, FindingCategory.DOCUMENTATION_GAP) and str(f.id) not in [a.related_finding_ids[0] for a in next_actions if a.related_finding_ids]:
                    next_actions.append(NextAction(
                        id=f"action-{action_idx:02d}",
                        priority="MEDIUM",
                        title=f"Address: {f.title}",
                        description=f.recommendation,
                        claim_type=KnowledgeClass.RECOMMENDED,
                        related_finding_ids=[str(f.id)],
                        evidence=f.evidence[:2],
                    ))
                    action_idx += 1
                    if len(next_actions) >= 5:
                        break

        # Fallback action if codebase is completely clean
        if not next_actions:
            next_actions.append(NextAction(
                id="action-01",
                priority="LOW",
                title="Maintain Current Architectural Hygiene",
                description="Continue standard test and documentation practices as new modules are developed.",
                claim_type=KnowledgeClass.RECOMMENDED,
                related_finding_ids=[],
                evidence=[],
            ))

        # Top Things to Know & Top Actions for Executive Summary
        top_things: list[ClaimItem] = []
        for f in facts.findings[:3]:
            top_things.append(ClaimItem(
                claim_type=KnowledgeClass.DERIVED if f.severity in (FindingSeverity.CRITICAL, FindingSeverity.HIGH) else KnowledgeClass.OBSERVED,
                title=f.title,
                statement=f"{f.description} {f.why_it_matters}",
                evidence=[EvidenceRef(
                    type=e.get("type", "CODE"),
                    file=e.get("file"),
                    symbol=e.get("symbol"),
                    lines=str(e.get("lines")) if e.get("lines") else None,
                ) for e in f.evidence[:2]],
            ))
        if not top_things:
            top_things.append(ClaimItem(
                claim_type=KnowledgeClass.OBSERVED,
                title="Modular Component Layout",
                statement=f"Analyzed {len(facts.files)} files with zero structural cycles or critical hotspots.",
                evidence=[],
            ))

        top_actions: list[ClaimItem] = []
        for act in next_actions[:3]:
            top_actions.append(ClaimItem(
                claim_type=KnowledgeClass.RECOMMENDED,
                title=act.title,
                statement=act.description,
                evidence=[],
            ))

        executive_summary = ExecutiveSummary(
            project_summary=project_summary,
            state_assessment=state_assessment,
            vital_metrics=vital_metrics,
            top_things_to_know=top_things,
            top_next_actions=top_actions,
        )

        metadata = {
            "project_name": facts.project.name,
            "project_slug": facts.project.slug,
            "snapshot_id": str(facts.snapshot.id),
            "commit_sha": facts.snapshot.commit_sha or "HEAD",
            "branch": facts.snapshot.branch or "main",
            "generated_at": facts.snapshot.created_at.isoformat() if facts.snapshot.created_at else "",
            "report_version": "1.0.0",
        }

        return ReportDocument(
            metadata=metadata,
            executive_summary=executive_summary,
            project_understanding=understanding,
            observed=observed_items[:10],
            discoveries=top_discoveries,
            risk_areas=risk_areas,
            technical_debt=tech_debt[:8],
            dependencies=important_deps[:8],
            testing_and_documentation=testing_and_docs,
            next_actions=next_actions[:6],
        )
