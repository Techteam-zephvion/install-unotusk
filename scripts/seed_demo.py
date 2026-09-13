"""
Unotusk MVP — Demo Seeding Script
=================================
Seeds a rich, realistic project environment for customer demos and testing.

Usage:
    python scripts/seed_demo.py
"""

import asyncio
import os
import sys
import tempfile
import uuid

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Default to unotusk if DATABASE_URL not set
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/unotusk",
)

from sqlalchemy import select

from apps.api.src.auth.security import hash_password
from apps.api.src.db.base import Base
from apps.api.src.db.session import AsyncSessionLocal, engine
from apps.api.src.models import *  # noqa: F403
from apps.api.src.models.enums import (
    IntegrationProvider,
    IntegrationStatus,
    KnowledgeCategory,
    MembershipRole,
    ProjectStatus,
    ReportStatus,
    SnapshotStatus,
)
from apps.api.src.models.integration import Integration
from apps.api.src.models.membership import OrganizationMembership
from apps.api.src.models.organization import Organization
from apps.api.src.models.project import Project
from apps.api.src.models.report import ProjectIntelligenceReport
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.models.user import User
from apps.api.src.schemas.knowledge import KnowledgeCreateRequest
from apps.api.src.services.discovery_engine.engine import ProjectDiscoveryEngine
from apps.api.src.services.ingestion_service import IngestionService
from apps.api.src.services.knowledge_service import KnowledgeService
from apps.api.src.services.report_engine.engine import ProjectReportEngine


async def seed_demo():
    print("==================================================")
    print("  UNOTUSK MVP — DEMO ENVIRONMENT SEEDER")
    print("==================================================")

    # Ensure tables exist
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True))
    except Exception as e:
        print(f"  Database schemas present ({e.__class__.__name__}). Continuing...")

    async with AsyncSessionLocal() as session:
        # 1. Demo User
        demo_email = "demo@unotusk.io"
        user_stmt = select(User).where(User.email == demo_email)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()

        if not user:
            user = User(
                id=uuid.uuid4(),
                email=demo_email,
                password_hash=hash_password("password123"),
                name="Alex Mercer (CTO)",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"✓ Created Demo User: {user.email} (password: password123)")
        else:
            print(f"✓ Found existing Demo User: {user.email}")

        # 2. Demo Organization
        org_slug = "acme-engineering"
        org_stmt = select(Organization).where(Organization.slug == org_slug)
        org_res = await session.execute(org_stmt)
        org = org_res.scalar_one_or_none()

        if not org:
            org = Organization(
                id=uuid.uuid4(),
                name="Acme Engineering",
                slug=org_slug,
            )
            session.add(org)
            await session.commit()
            await session.refresh(org)

            mem = OrganizationMembership(
                id=uuid.uuid4(),
                organization_id=org.id,
                user_id=user.id,
                role=MembershipRole.OWNER,
            )
            session.add(mem)
            await session.commit()
            print(f"✓ Created Demo Organization: {org.name}")
        else:
            print(f"✓ Found existing Demo Organization: {org.name}")

        # 3. Clean up existing demo project if present for idempotence
        proj_slug = "core-payment-engine"
        existing_p_stmt = select(Project).where(
            Project.organization_id == org.id,
            Project.slug == proj_slug,
        )
        existing_p = (await session.execute(existing_p_stmt)).scalar_one_or_none()
        if existing_p:
            print(f"  Cleaning up prior seed of project '{existing_p.name}'...")
            await session.delete(existing_p)
            await session.commit()

        project = Project(
            id=uuid.uuid4(),
            organization_id=org.id,
            name="Core Payment Engine",
            slug=proj_slug,
            description="Mission-critical transaction orchestration, tokenization, billing and payout platform.",
            status=ProjectStatus.READY,
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        print(f"✓ Created Demo Project: {project.name} (id: {project.id})")

        # 4. Connected Repository
        integration = Integration(
            id=uuid.uuid4(),
            project_id=project.id,
            provider=IntegrationProvider.GITHUB,
            status=IntegrationStatus.CONNECTED,
            external_id="gh-acme-payments",
            integration_metadata={"connected_by": user.email},
        )
        session.add(integration)

        repo = Repository(
            id=uuid.uuid4(),
            project_id=project.id,
            integration_id=integration.id,
            provider=IntegrationProvider.GITHUB,
            external_id="repo-acme-payments",
            owner="acme-corp",
            name="core-payment-engine",
            full_name="acme-corp/core-payment-engine",
            default_branch="main",
            url="https://github.com/acme-corp/core-payment-engine",
            is_private=True,
        )
        session.add(repo)

        snapshot = RepositorySnapshot(
            id=uuid.uuid4(),
            repository_id=repo.id,
            branch="main",
            status=SnapshotStatus.QUEUED,
        )
        session.add(snapshot)
        await session.commit()

        # 5. Build realistic demo codebase in temp directory and ingest
        print("  Ingesting demo codebase architecture...")
        with tempfile.TemporaryDirectory() as tmp_dir:
            src_dir = os.path.join(tmp_dir, "src")
            os.makedirs(src_dir, exist_ok=True)

            # Core Payment Gateway (High-coupling central hub)
            with open(os.path.join(src_dir, "payment_gateway.py"), "w") as f:
                f.write(
                    '"""Payment Gateway Core Orchestration Engine."""\n\n'
                    'class PaymentGateway:\n'
                    '    """Central vault interface for credit card, ACH, and crypto charges."""\n\n'
                    '    def __init__(self):\n'
                    '        self.vault_connected = True\n\n'
                    '    def process_charge(self, customer_id: str, amount_cents: int, currency: str = "USD"):\n'
                    '        """Process tokenized payment against upstream providers."""\n'
                    '        return {"status": "succeeded", "charge_id": "ch_98472948291", "amount": amount_cents}\n\n'
                    '    def refund_charge(self, charge_id: str, amount_cents: int):\n'
                    '        return {"status": "refunded", "refund_id": "re_847192847"}\n'
                )

            # Invoice Module
            with open(os.path.join(src_dir, "invoice_service.py"), "w") as f:
                f.write(
                    'from src.payment_gateway import PaymentGateway\n\n'
                    'class InvoiceService:\n'
                    '    def __init__(self):\n'
                    '        self.gateway = PaymentGateway()\n\n'
                    '    def generate_and_settle(self, invoice_id: str, user_id: str, amount: int):\n'
                    '        return self.gateway.process_charge(user_id, amount)\n'
                )

            # Subscriptions Module
            with open(os.path.join(src_dir, "subscription_engine.py"), "w") as f:
                f.write(
                    'from src.payment_gateway import PaymentGateway\n'
                    'from src.invoice_service import InvoiceService\n\n'
                    'class SubscriptionEngine:\n'
                    '    def __init__(self):\n'
                    '        self.gateway = PaymentGateway()\n'
                    '        self.invoices = InvoiceService()\n\n'
                    '    def renew_subscription(self, sub_id: str, customer_id: str, plan_fee: int):\n'
                    '        return self.gateway.process_charge(customer_id, plan_fee)\n'
                )

            # Fraud Detection Module
            with open(os.path.join(src_dir, "fraud_detector.py"), "w") as f:
                f.write(
                    'from src.payment_gateway import PaymentGateway\n\n'
                    'class FraudDetector:\n'
                    '    def __init__(self):\n'
                    '        self.gw = PaymentGateway()\n\n'
                    '    def evaluate_risk(self, ip: str, customer_id: str, amount: int):\n'
                    '        if amount > 5000000:\n'
                    '            return {"action": "review", "score": 92}\n'
                    '        return {"action": "allow", "score": 12}\n'
                )

            # Webhook Handler
            with open(os.path.join(src_dir, "webhook_handler.py"), "w") as f:
                f.write(
                    'from src.payment_gateway import PaymentGateway\n\n'
                    'class WebhookHandler:\n'
                    '    def __init__(self):\n'
                    '        self.gateway = PaymentGateway()\n\n'
                    '    def handle_stripe_event(self, payload: dict):\n'
                    '        event_type = payload.get("type")\n'
                    '        if event_type == "charge.dispute.created":\n'
                    '            return {"handled": True}\n'
                    '        return {"handled": False}\n'
                )

            # Circular dependency pair: auth_token <-> user_session
            with open(os.path.join(src_dir, "auth_token.py"), "w") as f:
                f.write(
                    'from src.user_session import UserSession\n\n'
                    'class AuthToken:\n'
                    '    def validate(self, token_str: str):\n'
                    '        session = UserSession()\n'
                    '        return session.is_valid(token_str)\n'
                )

            with open(os.path.join(src_dir, "user_session.py"), "w") as f:
                f.write(
                    'from src.auth_token import AuthToken\n\n'
                    'class UserSession:\n'
                    '    def is_valid(self, session_id: str):\n'
                    '        token = AuthToken()\n'
                    '        return True\n'
                )

            # Legacy crypto module
            with open(os.path.join(src_dir, "legacy_des_crypto.py"), "w") as f:
                f.write(
                    '# DEPRECATED: Legacy DES cipher implementation for v1 merchant callbacks.\n'
                    '# Do not use for new endpoints.\n'
                    'class LegacyDESCrypto:\n'
                    '    def decrypt_payload(self, raw_bytes: bytes):\n'
                    '        return "decrypted_string"\n'
                )

            snapshot_id = snapshot.id
            await IngestionService.run_ingestion(snapshot_id, override_local_dir=tmp_dir)

        print(f"✓ Ingestion Complete: Snapshot {snapshot.id} indexed.")

        # 6. Run Discovery Engine
        print("  Running Discovery Pipeline...")
        discovery_run_id = uuid.uuid4()
        findings = await ProjectDiscoveryEngine.run_discovery(
            project_id=project.id,
            snapshot_id=snapshot.id,
            discovery_run_id=discovery_run_id,
            session=session,
        )
        print(f"✓ Discovery Complete: {len(findings)} structural findings identified.")

        # 7. Seed Customer Knowledge
        print("  Seeding Customer Knowledge items...")
        await KnowledgeService.create_knowledge(
            session=session,
            user_id=user.id,
            project_id=project.id,
            data=KnowledgeCreateRequest(
                category=KnowledgeCategory.ARCHITECTURE_DECISION,
                title="PCI DSS Tokenization Vault Boundary",
                content="PaymentGateway is intentionally the single hub for all billing operations because it routes through an isolated PCI-compliant token vault proxy.",
                related_symbol="PaymentGateway",
                related_file_path="src/payment_gateway.py",
            ),
        )

        await KnowledgeService.create_knowledge(
            session=session,
            user_id=user.id,
            project_id=project.id,
            data=KnowledgeCreateRequest(
                category=KnowledgeCategory.EXCEPTION,
                title="Legacy DES Crypto Sunsetting Timeline",
                content="legacy_des_crypto.py is maintained solely for backward compatibility with European enterprise merchant POS terminals until Q4 2026.",
                related_file_path="src/legacy_des_crypto.py",
                related_symbol="LegacyDESCrypto",
            ),
        )

        await KnowledgeService.create_knowledge(
            session=session,
            user_id=user.id,
            project_id=project.id,
            data=KnowledgeCreateRequest(
                category=KnowledgeCategory.BUSINESS_RULE,
                title="Tier-3 High Risk Merchant Reserve Delay",
                content="Charges exceeding $50,000 for Tier-3 merchants trigger automated 72-hour escrow hold before gateway clearance.",
            ),
        )
        print("✓ Customer Knowledge Seeded: 3 active entries.")

        # 8. Generate Flagship Intelligence Report
        print("  Generating Flagship Intelligence Report...")
        report = ProjectIntelligenceReport(
            id=uuid.uuid4(),
            project_id=project.id,
            snapshot_id=snapshot.id,
            discovery_run_id=discovery_run_id,
            status=ReportStatus.GENERATING,
            report_version="1.0.0",
            summary="Flagship Intelligence Report for Core Payment Engine",
            report_data={},
        )
        session.add(report)
        await session.commit()

        completed_report = await ProjectReportEngine.generate_report(
            project_id=project.id,
            snapshot_id=snapshot.id,
            discovery_run_id=discovery_run_id,
            report_id=report.id,
            session=session,
        )
        print(f"✓ Flagship Intelligence Report Ready: {completed_report.id}")

    print("\n==================================================")
    print("  DEMO READY!")
    print(f"  Login: {demo_email} / password123")
    print(f"  Project URL: http://localhost:3000/projects/{project.id}")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(seed_demo())
