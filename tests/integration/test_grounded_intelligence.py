import os
import tempfile
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.enums import IntegrationProvider, IntegrationStatus, SnapshotStatus
from apps.api.src.models.integration import Integration
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.services.ingestion_service import IngestionService
from apps.api.src.services.intelligence_service import IntelligenceService


@pytest.mark.asyncio
async def test_end_to_end_grounded_intelligence(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    # 1. Setup Project hierarchy
    user = await create_test_user(email="intel-tester@unotusk.io")
    org, _ = await create_test_org(user=user, name="Intel Org")
    project = await create_test_project(organization=org, name="Intel Project")

    integration = Integration(
        id=uuid.uuid4(),
        project_id=project.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id="gh-intel-123",
        integration_metadata={},
    )
    db_session.add(integration)

    repository = Repository(
        id=uuid.uuid4(),
        project_id=project.id,
        integration_id=integration.id,
        provider=IntegrationProvider.GITHUB,
        external_id="repo-intel-456",
        owner="intel-owner",
        name="intel-repo",
        full_name="intel-owner/intel-repo",
        default_branch="main",
        url="https://github.com/intel-owner/intel-repo",
        is_private=False,
    )
    db_session.add(repository)

    snapshot = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repository.id,
        branch="main",
        status=SnapshotStatus.QUEUED,
    )
    db_session.add(snapshot)
    await db_session.commit()

    # 2. Ingest Sample Codebase
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
        auth_file = os.path.join(tmpdir, "src", "auth.py")
        with open(auth_file, "w") as f:
            f.write(
                "import os\n\nclass AuthService:\n    def login(self, username, password):\n        return True\n"
            )

        user_file = os.path.join(tmpdir, "src", "user.py")
        with open(user_file, "w") as f:
            f.write(
                "class UserService:\n    def get_profile(self, user_id):\n        return {'user_id': user_id}\n"
            )

        await IngestionService.run_ingestion(snapshot.id, override_local_dir=tmpdir)

    # 3. Ask Grounded Question
    answer_res = await IntelligenceService.ask_question(
        session=db_session,
        user_id=user.id,
        project_id=project.id,
        question="How does AuthService.login work?",
    )

    assert answer_res.confidence in ("HIGH", "MEDIUM")
    assert answer_res.conversation_id is not None
    assert answer_res.role == "assistant"
    assert len(answer_res.content) > 20

    # Verify evidence references
    evidence_files = [e.file for e in answer_res.evidence]
    assert any("auth.py" in f for f in evidence_files)

    evidence_symbols = [e.symbol for e in answer_res.evidence if e.symbol]
    assert any("AuthService" in s or "login" in s for s in evidence_symbols)

    # 4. Verify Conversation and Messages Persistence
    messages = await IntelligenceService.get_conversation_messages(
        session=db_session,
        user_id=user.id,
        project_id=project.id,
        conversation_id=answer_res.conversation_id,
    )
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "How does AuthService.login work?"
    assert messages[1].role == "assistant"
    assert len(messages[1].evidence) >= 1

    # 5. Verify Context Search Debug
    debug_res = await IntelligenceService.debug_search_context(
        session=db_session,
        user_id=user.id,
        project_id=project.id,
        query="AuthService",
    )
    assert debug_res.candidates_count >= 1
    assert any(c.name == "AuthService" for c in debug_res.ranked_candidates)
