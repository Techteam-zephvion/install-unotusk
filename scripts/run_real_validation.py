import asyncio
import json
import logging
import os
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select

from apps.api.src.config.settings import settings
from apps.api.src.db.session import AsyncSessionLocal
from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.enums import (
    IntegrationProvider,
    IntegrationStatus,
    KnowledgeCategory,
    KnowledgeStatus,
    MembershipRole,
    ProjectStatus,
    SnapshotStatus,
)
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.integration import Integration
from apps.api.src.models.knowledge import ProjectKnowledge
from apps.api.src.models.membership import OrganizationMembership
from apps.api.src.models.organization import Organization
from apps.api.src.models.project import Project
from apps.api.src.models.report import ProjectIntelligenceReport
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.models.user import User
from apps.api.src.services.context_engine.engine import ProjectContextEngine
from apps.api.src.services.discovery_engine.engine import ProjectDiscoveryEngine
from apps.api.src.services.ingestion_service import IngestionService
from apps.api.src.services.llm.groq import GroqProvider
from apps.api.src.services.report_engine.engine import ProjectReportEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("validation-runner")


def utc_now() -> datetime:
    return datetime.now(UTC)


async def run_validation():
    results = {
        "timestamp": utc_now().isoformat(),
        "repository": "psf/requests",
        "llm_provider": settings.LLM_PROVIDER,
        "groq_model": settings.GROQ_MODEL,
        "groq_api_key_set": bool(settings.GROQ_API_KEY),
        "metrics": {},
        "grounded_ask": [],
        "discoveries": [],
        "reports": {},
        "customer_knowledge_flow": {},
        "isolation_test": {},
        "security_test": {},
    }

    target_repo_dir = os.path.abspath("validation_repos/requests")
    if not os.path.exists(target_repo_dir):
        raise RuntimeError(f"Target repository not found at {target_repo_dir}")

    async with AsyncSessionLocal() as session:
        logger.info("==================================================")
        logger.info("STAGE 1: SEED VALIDATION ORG & PROJECT")
        logger.info("==================================================")

        # Create or find test user & org
        user_stmt = select(User).where(User.email == "validator@unotusk.com")
        user = (await session.execute(user_stmt)).scalar_one_or_none()
        if not user:
            user = User(
                id=uuid.uuid4(),
                email="validator@unotusk.com",
                name="Validation Agent",
                password_hash="argon2-hashed-val",
            )
            session.add(user)
            await session.flush()

        org_stmt = select(Organization).where(Organization.slug == "requests-validation-org")
        org = (await session.execute(org_stmt)).scalar_one_or_none()
        if not org:
            org = Organization(
                id=uuid.uuid4(),
                name="Requests Validation Org",
                slug="requests-validation-org",
            )
            session.add(org)
            await session.flush()
            membership = OrganizationMembership(
                id=uuid.uuid4(),
                organization_id=org.id,
                user_id=user.id,
                role=MembershipRole.OWNER,
            )
            session.add(membership)
            await session.flush()

        # Clean existing project if present
        proj_stmt = select(Project).where(
            Project.organization_id == org.id, Project.slug == "psf-requests"
        )
        existing_proj = (await session.execute(proj_stmt)).scalar_one_or_none()
        if existing_proj:
            logger.info(f"Cleaning existing project {existing_proj.id}")
            await session.execute(delete(Project).where(Project.id == existing_proj.id))
            await session.commit()

        project = Project(
            id=uuid.uuid4(),
            organization_id=org.id,
            name="psf/requests",
            slug="psf-requests",
            description="A real-world Python HTTP library validation target",
            status=ProjectStatus.CREATED,
        )
        session.add(project)
        await session.flush()

        integration = Integration(
            id=uuid.uuid4(),
            project_id=project.id,
            provider=IntegrationProvider.GITHUB,
            status=IntegrationStatus.CONNECTED,
            external_id="ext-gh-requests",
            integration_metadata={"repo": "psf/requests"},
        )
        session.add(integration)
        await session.flush()

        repo = Repository(
            id=uuid.uuid4(),
            project_id=project.id,
            integration_id=integration.id,
            provider=IntegrationProvider.GITHUB,
            external_id="123456",
            owner="psf",
            name="requests",
            full_name="psf/requests",
            default_branch="main",
            url="https://github.com/psf/requests",
            is_private=False,
            repo_metadata={},
        )
        session.add(repo)
        await session.flush()

        snapshot = RepositorySnapshot(
            id=uuid.uuid4(),
            repository_id=repo.id,
            commit_sha="HEAD",
            status=SnapshotStatus.QUEUED,
        )
        session.add(snapshot)
        await session.commit()

        logger.info(f"Created project {project.id}, snapshot {snapshot.id}")

    # STAGE 2: INGESTION PIPELINE
    logger.info("==================================================")
    logger.info("STAGE 2: RUNNING REPOSITORY INGESTION")
    logger.info("==================================================")
    t0_ingest = time.time()
    await IngestionService.run_ingestion(
        snapshot_id=snapshot.id,
        override_local_dir=target_repo_dir,
    )
    ingestion_duration = time.time() - t0_ingest

    async with AsyncSessionLocal() as session:
        files_count = (
            await session.execute(
                select(func.count(RepositoryFile.id)).where(RepositoryFile.snapshot_id == snapshot.id)
            )
        ).scalar_one()
        symbols_count = (
            await session.execute(
                select(func.count(CodeSymbol.id))
                .join(RepositoryFile, RepositoryFile.id == CodeSymbol.file_id)
                .where(RepositoryFile.snapshot_id == snapshot.id)
            )
        ).scalar_one()
        deps_count = (
            await session.execute(
                select(func.count(CodeDependency.id))
                .join(RepositoryFile, RepositoryFile.id == CodeDependency.source_file_id)
                .where(RepositoryFile.snapshot_id == snapshot.id)
            )
        ).scalar_one()
        chunks_count = (
            await session.execute(
                select(func.count(CodeChunk.id))
                .join(RepositoryFile, RepositoryFile.id == CodeChunk.file_id)
                .where(RepositoryFile.snapshot_id == snapshot.id)
            )
        ).scalar_one()

        results["metrics"]["ingestion_time_s"] = round(ingestion_duration, 3)
        results["metrics"]["files_count"] = files_count
        results["metrics"]["symbols_count"] = symbols_count
        results["metrics"]["dependencies_count"] = deps_count
        results["metrics"]["chunks_count"] = chunks_count

        logger.info(
            f"Ingestion complete in {ingestion_duration:.2f}s: {files_count} files, {symbols_count} symbols, {deps_count} dependencies, {chunks_count} chunks"
        )

    # STAGE 3: PROACTIVE DISCOVERY
    logger.info("==================================================")
    logger.info("STAGE 3: RUNNING PROACTIVE DISCOVERY")
    logger.info("==================================================")
    t0_disc = time.time()
    findings = await ProjectDiscoveryEngine.run_discovery(
        project_id=project.id,
        snapshot_id=snapshot.id,
    )
    discovery_duration = time.time() - t0_disc
    results["metrics"]["discovery_time_s"] = round(discovery_duration, 3)
    results["metrics"]["total_findings"] = len(findings)

    logger.info(f"Discovery complete in {discovery_duration:.2f}s: {len(findings)} findings discovered.")

    for f in findings:
        aff_file = f.finding_metadata.get("file") or (f.evidence[0].get("file") if f.evidence else "N/A")
        aff_sym = f.finding_metadata.get("symbol") or (f.evidence[0].get("symbol") if f.evidence else "N/A")
        finding_info = {
            "title": f.title,
            "category": f.category.value if hasattr(f.category, "value") else str(f.category),
            "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
            "confidence": f.confidence.value if hasattr(f.confidence, "value") else str(f.confidence),
            "affected_file": aff_file,
            "affected_symbol": aff_sym,
            "summary": f.description,
            "impact": f.why_it_matters,
            "recommendation": f.recommendation,
            "evidence": f.evidence,
        }
        results["discoveries"].append(finding_info)
        logger.info(f" -> [{finding_info['severity']}] [{finding_info['category']}] {f.title[:80]} (File: {aff_file})")

    # STAGE 4: GROUNDED ASK VALIDATION (5 Categories + Hallucination Test)
    logger.info("==================================================")
    logger.info("STAGE 4: GROUNDED ASK VALIDATION (GROQ)")
    logger.info("==================================================")

    provider = GroqProvider()
    context_engine = ProjectContextEngine(llm_provider=provider)

    test_questions = [
        {
            "category": "A. Project Understanding",
            "question": "What are the main architectural components and entry points of this repository?",
            "expected_entities": ["api.py", "sessions.py", "models.py", "Session", "Request"],
            "is_hallucination_test": False,
        },
        {
            "category": "B. Dependency Questions",
            "question": "What components depend on Session and HTTPAdapter, and what external libraries are used?",
            "expected_entities": ["Session", "HTTPAdapter", "urllib3", "adapters.py", "sessions.py"],
            "is_hallucination_test": False,
        },
        {
            "category": "C. Architecture Questions",
            "question": "How does an HTTP request flow from requests.api to prepared request dispatching?",
            "expected_entities": ["api.py", "sessions.py", "PreparedRequest", "models.py"],
            "is_hallucination_test": False,
        },
        {
            "category": "D. Change-Risk Questions",
            "question": "What components could be affected if the PreparedRequest model changes?",
            "expected_entities": ["PreparedRequest", "models.py", "sessions.py", "adapters.py"],
            "is_hallucination_test": False,
        },
        {
            "category": "E. Evidence Questions",
            "question": "Where is authentication implemented and what classes handle it in this codebase?",
            "expected_entities": ["auth.py", "AuthBase", "HTTPBasicAuth"],
            "is_hallucination_test": False,
        },
        {
            "category": "MANDATORY HALLUCINATION TEST",
            "question": "How does the QuantumPaymentController handle settlement in this codebase?",
            "expected_entities": [],
            "is_hallucination_test": True,
        },
    ]

    async with AsyncSessionLocal() as session:
        for item in test_questions:
            t0_ask = time.time()
            answer = await context_engine.investigate(
                session=session,
                snapshot_id=snapshot.id,
                question=item["question"],
                project_id=project.id,
            )
            ask_duration = time.time() - t0_ask

            evidence_files = [e.get("file") for e in answer.evidence if e.get("file")]
            evidence_symbols = [e.get("symbol") for e in answer.evidence if e.get("symbol")]

            # Evaluation
            if item["is_hallucination_test"]:
                # Should not hallucinate QuantumPaymentController as existing or should state no evidence found
                hallucinated = (
                    "settlement logic" in answer.content.lower()
                    and "quantumpaymentcontroller" in answer.content.lower()
                    and "not found" not in answer.content.lower()
                    and "no matching" not in answer.content.lower()
                    and "insufficient" not in answer.content.lower()
                )
                pass_status = not hallucinated
                assessment = "PASS" if pass_status else "FAIL"
            else:
                supported = any(
                    ent.lower() in answer.content.lower() or any(ent.lower() in str(ef).lower() for ef in evidence_files)
                    for ent in item["expected_entities"]
                )
                assessment = "SUPPORTED" if supported else "PARTIAL"

            record = {
                "category": item["category"],
                "question": item["question"],
                "confidence": answer.confidence,
                "assessment": assessment,
                "evidence_count": len(answer.evidence),
                "evidence_files": list(set(evidence_files)),
                "evidence_symbols": list(set(evidence_symbols)),
                "response_preview": answer.content[:400] + "...",
                "full_content": answer.content,
                "debug_signals": answer.debug_signals,
                "response_time_s": round(ask_duration, 3),
            }
            results["grounded_ask"].append(record)
            logger.info(f"Ask [{item['category']}] -> {assessment} (Conf: {answer.confidence}, {len(evidence_files)} files, {ask_duration:.2f}s)")

    # STAGE 5: REPORT v1 GENERATION
    logger.info("==================================================")
    logger.info("STAGE 5: INTELLIGENCE REPORT v1 (BEFORE KNOWLEDGE)")
    logger.info("==================================================")
    t0_rep1 = time.time()
    report_v1 = await ProjectReportEngine.generate_report(
        project_id=project.id,
        snapshot_id=snapshot.id,
    )
    report_v1_duration = time.time() - t0_rep1
    results["metrics"]["report_v1_time_s"] = round(report_v1_duration, 3)

    results["reports"]["v1"] = {
        "id": str(report_v1.id),
        "status": report_v1.status.value if hasattr(report_v1.status, "value") else str(report_v1.status),
        "summary": report_v1.summary,
        "vital_metrics": report_v1.report_data.get("executive_summary", {}).get("vital_metrics", {}),
        "top_discoveries_count": len(report_v1.report_data.get("discoveries", [])),
        "risk_areas_count": len(report_v1.report_data.get("risk_areas", [])),
        "observed_facts_count": len(report_v1.report_data.get("observed", [])),
    }
    logger.info(f"Report v1 generated in {report_v1_duration:.2f}s (Status: {results['reports']['v1']['status']})")
    logger.info(f"Summary v1: {report_v1.summary}")

    # STAGE 6: CUSTOMER PROJECT KNOWLEDGE INGESTION & GROUNDED ASK v2
    logger.info("==================================================")
    logger.info("STAGE 6: CUSTOMER PROJECT KNOWLEDGE INTEGRATION")
    logger.info("==================================================")

    knowledge_title = "Intentional Centralization of HTTPAdapter & Session"
    knowledge_content = (
        "The high coupling between Session and HTTPAdapter is an intentional architectural pattern. "
        "Session manages high-level connection configuration, cookies, and authentication state, "
        "while HTTPAdapter encapsulates low-level urllib3 connection pooling and retries."
    )

    async with AsyncSessionLocal() as session:
        pk = ProjectKnowledge(
            id=uuid.uuid4(),
            project_id=project.id,
            title=knowledge_title,
            content=knowledge_content,
            category=KnowledgeCategory.ARCHITECTURE_DECISION,
            source_type="CUSTOMER",
            status=KnowledgeStatus.ACTIVE,
            created_by=user.id,
            related_file_path="src/requests/adapters.py",
            related_symbol="HTTPAdapter",
            knowledge_metadata={"component": "HTTPAdapter", "intent": "connection-pooling-architecture"},
        )
        session.add(pk)
        await session.commit()
        await session.refresh(pk)
        knowledge_id = pk.id
        logger.info(f"Added Customer Knowledge: {knowledge_id} - '{knowledge_title}'")

    # Ask Grounded Ask post-knowledge
    async with AsyncSessionLocal() as session:
        q_knowledge = "Why do Session and HTTPAdapter have high coupling?"
        ans_post_knowledge = await context_engine.investigate(
            session=session,
            snapshot_id=snapshot.id,
            question=q_knowledge,
            project_id=project.id,
        )

        results["customer_knowledge_flow"]["post_knowledge_ask"] = {
            "question": q_knowledge,
            "confidence": ans_post_knowledge.confidence,
            "has_customer_attribution": "CUSTOMER" in ans_post_knowledge.content or "intentional" in ans_post_knowledge.content.lower(),
            "has_code_evidence": len(ans_post_knowledge.evidence) > 0,
            "content": ans_post_knowledge.content,
            "debug_signals": ans_post_knowledge.debug_signals,
        }
        logger.info(f"Post-knowledge ask answered (Customer context integrated: {results['customer_knowledge_flow']['post_knowledge_ask']['has_customer_attribution']})")

    # STAGE 7: REPORT v2 GENERATION (POST-KNOWLEDGE)
    logger.info("==================================================")
    logger.info("STAGE 7: INTELLIGENCE REPORT v2 (POST-KNOWLEDGE)")
    logger.info("==================================================")
    t0_rep2 = time.time()
    report_v2 = await ProjectReportEngine.generate_report(
        project_id=project.id,
        snapshot_id=snapshot.id,
    )
    report_v2_duration = time.time() - t0_rep2
    results["metrics"]["report_v2_time_s"] = round(report_v2_duration, 3)

    # Check that Report v1 in DB was not overwritten
    async with AsyncSessionLocal() as session:
        v1_check = (await session.execute(
            select(ProjectIntelligenceReport).where(ProjectIntelligenceReport.id == report_v1.id)
        )).scalar_one()

        results["reports"]["v2"] = {
            "id": str(report_v2.id),
            "status": report_v2.status.value if hasattr(report_v2.status, "value") else str(report_v2.status),
            "summary": report_v2.summary,
            "v1_preserved": v1_check.summary == report_v1.summary,
            "has_project_knowledge": len(report_v2.report_data.get("project_knowledge", [])) > 0,
        }
        logger.info(f"Report v2 generated in {report_v2_duration:.2f}s (v1 preserved: {results['reports']['v2']['v1_preserved']}, knowledge reflected: {results['reports']['v2']['has_project_knowledge']})")

    # STAGE 8: ARCHIVE CUSTOMER KNOWLEDGE TEST
    logger.info("==================================================")
    logger.info("STAGE 8: ARCHIVE CUSTOMER KNOWLEDGE TEST")
    logger.info("==================================================")
    async with AsyncSessionLocal() as session:
        pk_record = (await session.execute(
            select(ProjectKnowledge).where(ProjectKnowledge.id == knowledge_id)
        )).scalar_one()
        pk_record.status = KnowledgeStatus.ARCHIVED
        await session.commit()
        logger.info(f"Archived knowledge item {knowledge_id}")

        ans_post_archive = await context_engine.investigate(
            session=session,
            snapshot_id=snapshot.id,
            question=q_knowledge,
            project_id=project.id,
        )

        # Archived knowledge should NOT be retrieved in customer context
        archived_knowledge_count = ans_post_archive.debug_signals.get("customer_knowledge_count", 0)
        results["customer_knowledge_flow"]["post_archive_test"] = {
            "customer_knowledge_count_retrieved": archived_knowledge_count,
            "pass_archive_exclusion": archived_knowledge_count == 0,
        }
        logger.info(f"Archive test result: {archived_knowledge_count} active customer items retrieved (Pass: {archived_knowledge_count == 0})")

    # STAGE 9: MULTI-PROJECT / MULTI-TENANT ISOLATION TEST
    logger.info("==================================================")
    logger.info("STAGE 9: MULTI-PROJECT / MULTI-TENANT ISOLATION")
    logger.info("==================================================")
    async with AsyncSessionLocal() as session:
        suffix = uuid.uuid4().hex[:6]
        project_b = Project(
            id=uuid.uuid4(),
            organization_id=org.id,
            name=f"Project B Isolated {suffix}",
            slug=f"proj-b-isolated-{suffix}",
            description="Tenant isolation check",
            status=ProjectStatus.CREATED,
        )
        session.add(project_b)
        await session.flush()

        integration_b = Integration(
            id=uuid.uuid4(),
            project_id=project_b.id,
            provider=IntegrationProvider.GITHUB,
            status=IntegrationStatus.CONNECTED,
            external_id=f"ext-gh-isolated-{suffix}",
            integration_metadata={"repo": "org/isolated-repo-b"},
        )
        session.add(integration_b)
        await session.flush()

        repo_b = Repository(
            id=uuid.uuid4(),
            project_id=project_b.id,
            integration_id=integration_b.id,
            provider=IntegrationProvider.GITHUB,
            external_id=f"repo-{suffix}",
            owner="org",
            name="isolated-repo-b",
            full_name="org/isolated-repo-b",
            default_branch="main",
            url="https://github.com/org/isolated-repo-b",
            is_private=False,
            repo_metadata={},
        )
        session.add(repo_b)
        await session.flush()

        snapshot_b = RepositorySnapshot(
            id=uuid.uuid4(),
            repository_id=repo_b.id,
            commit_sha="HEAD",
            status=SnapshotStatus.COMPLETED,
        )
        session.add(snapshot_b)
        await session.commit()

        # Ingest a single file into project B
        file_b = RepositoryFile(
            id=uuid.uuid4(),
            snapshot_id=snapshot_b.id,
            path="isolated_service.py",
            filename="isolated_service.py",
            extension=".py",
            language="Python",
            size_bytes=100,
            line_count=10,
            content_hash="hashb",
            is_test=False,
            is_binary=False,
            is_generated=False,
            parser_supported=True,
        )
        session.add(file_b)
        await session.commit()

        # Query Project B context engine
        ans_b = await context_engine.investigate(
            session=session,
            snapshot_id=snapshot_b.id,
            question="Why do Session and HTTPAdapter have high coupling?",
            project_id=project_b.id,
        )

        b_has_a_files = any("requests" in str(e.get("file")) for e in ans_b.evidence)
        b_has_a_knowledge = ans_b.debug_signals.get("customer_knowledge_count", 0) > 0

        results["isolation_test"] = {
            "project_b_id": str(project_b.id),
            "leaked_files_from_a": b_has_a_files,
            "leaked_knowledge_from_a": b_has_a_knowledge,
            "pass_isolation": not b_has_a_files and not b_has_a_knowledge,
        }
        logger.info(f"Isolation Test Pass: {results['isolation_test']['pass_isolation']}")

    # STAGE 10: SECURITY CHECK
    logger.info("==================================================")
    logger.info("STAGE 10: SECURITY VERIFICATION")
    logger.info("==================================================")
    # Check that GROQ_API_KEY is not in report or evidence
    groq_in_report = "gsk_" in json.dumps(results["reports"])
    groq_in_evidence = "gsk_" in json.dumps(results["grounded_ask"])
    results["security_test"] = {
        "api_key_in_report": groq_in_report,
        "api_key_in_evidence": groq_in_evidence,
        "pass_security": not groq_in_report and not groq_in_evidence,
    }
    logger.info(f"Security Test Pass: {results['security_test']['pass_security']}")

    # Output results to json artifact
    with open("scripts/validation_results.json", "w") as out:
        json.dump(results, out, indent=2)
    logger.info("Saved validation results to scripts/validation_results.json")

    return results


if __name__ == "__main__":
    asyncio.run(run_validation())
