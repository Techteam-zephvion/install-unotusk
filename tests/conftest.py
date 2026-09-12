import os
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Set test environment
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "true"
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/unotusk_test",
)
os.environ["DATABASE_URL"] = TEST_DB_URL

from apps.api.src.api.dependencies.database import get_db
from apps.api.src.auth.security import create_access_token, hash_password
from apps.api.src.main import app
from apps.api.src.models.enums import MembershipRole, ProjectStatus
from apps.api.src.models.membership import OrganizationMembership
from apps.api.src.models.organization import Organization
from apps.api.src.models.project import Project
from apps.api.src.models.user import User

test_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(autouse=True)
async def clean_database():
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE integrations, projects, organization_memberships, organizations, users CASCADE;"
            )
        )
    yield


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
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
        await db_session.refresh(user)
        return user

    return _create


@pytest_asyncio.fixture
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
        await db_session.refresh(org)
        await db_session.refresh(membership)
        return org, membership

    return _create


@pytest_asyncio.fixture
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
        await db_session.refresh(proj)
        return proj

    return _create


@pytest.fixture
def auth_headers():
    def _headers(user: User) -> dict[str, str]:
        token = create_access_token(subject=str(user.id), extra_claims={"email": user.email})
        return {"Authorization": f"Bearer {token}"}

    return _headers
