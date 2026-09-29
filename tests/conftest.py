import asyncio
import inspect
import os
import sys
import uuid
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

# Provide mock for asyncpg if not installed in host environment
try:
    import asyncpg  # noqa: F401
except ImportError:
    sys.modules["asyncpg"] = MagicMock()

import pytest

try:
    import pytest_asyncio

    _HAS_PYTEST_ASYNCIO = True
    async_fixture = pytest_asyncio.fixture
except ImportError:
    pytest_asyncio = None
    _HAS_PYTEST_ASYNCIO = False
    async_fixture = pytest.fixture

from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Set test environment
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "true"
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/unotusk_test",
    ),
)
os.environ["DATABASE_URL"] = TEST_DB_URL

from apps.api.src.api.dependencies.database import get_db
from apps.api.src.auth.security import create_access_token, hash_password
from apps.api.src.models.enums import MembershipRole, ProjectStatus
from apps.api.src.models.membership import OrganizationMembership
from apps.api.src.models.organization import Organization
from apps.api.src.models.project import Project
from apps.api.src.models.user import User

try:
    test_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool, echo=False)
    TestSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )
except Exception:
    test_engine = None
    TestSessionLocal = None


def pytest_pyfunc_call(pyfuncitem):
    """Allows running async def test functions in unit tests without requiring pytest-asyncio plugin."""
    if not _HAS_PYTEST_ASYNCIO and inspect.iscoroutinefunction(pyfuncitem.obj):
        args = [
            pyfuncitem.funcargs[arg]
            for arg in pyfuncitem._fixtureinfo.argnames
            if arg in pyfuncitem.funcargs
        ]
        asyncio.run(pyfuncitem.obj(*args))
        return True


@async_fixture(autouse=True)
async def clean_database():
    if test_engine is None:
        yield
        return
    try:
        async with test_engine.begin() as conn:
            await conn.execute(
                text(
                    "TRUNCATE TABLE findings, discovery_runs, "
                    "project_intelligence_reports, project_knowledge, messages, conversations, "
                    "code_dependencies, code_chunks, code_symbols, repository_files, "
                    "repository_snapshots, repositories, integrations, projects, "
                    "organization_memberships, organizations, users CASCADE;"
                )
            )
    except Exception:
        pass
    yield


@async_fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    if TestSessionLocal is None:
        yield None
        return
    async with TestSessionLocal() as session:
        yield session


@async_fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    if TestSessionLocal is None:
        yield None
        return

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    try:
        from apps.api.src.main import app
    except ImportError:
        yield None
        return

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@async_fixture
async def create_test_user(db_session: AsyncSession):
    async def _create(
        email: str = "test@example.com",
        name: str = "Test User",
        password: str = "Password123!",
    ) -> User:
        user = User(
            id=uuid.uuid4(),
            email=email.lower(),
            name=name,
            password_hash=hash_password(password),
        )
        db_session.add(user)
        await db_session.commit()
        return user

    return _create


@async_fixture
async def create_test_org(db_session: AsyncSession):
    async def _create(
        user: User,
        name: str = "Test Org",
        slug: str | None = None,
        role: MembershipRole = MembershipRole.OWNER,
    ) -> tuple[Organization, OrganizationMembership]:
        org_slug = slug or f"org-{uuid.uuid4().hex[:6]}"
        org = Organization(
            id=uuid.uuid4(),
            name=name,
            slug=org_slug,
        )
        db_session.add(org)
        await db_session.flush()

        membership = OrganizationMembership(
            id=uuid.uuid4(),
            organization_id=org.id,
            user_id=user.id,
            role=role,
        )
        db_session.add(membership)
        await db_session.commit()
        return org, membership

    return _create


@async_fixture
async def create_test_project(db_session: AsyncSession):
    async def _create(
        organization: Organization,
        name: str = "Test Project",
        slug: str | None = None,
        description: str | None = "A test project description",
    ) -> Project:
        proj_slug = slug or f"proj-{uuid.uuid4().hex[:6]}"
        proj = Project(
            id=uuid.uuid4(),
            organization_id=organization.id,
            name=name,
            slug=proj_slug,
            description=description,
            status=ProjectStatus.CREATED,
        )
        db_session.add(proj)
        await db_session.commit()
        return proj

    return _create


@pytest.fixture
def auth_headers():
    def _headers(user: User) -> dict[str, str]:
        token = create_access_token(subject=str(user.id), extra_claims={"email": user.email})
        return {"Authorization": f"Bearer {token}"}

    return _headers
