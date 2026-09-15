import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.enums import (
    IntegrationProvider,
    IntegrationStatus,
    ProjectStatus,
)
from apps.api.src.models.integration import Integration
from apps.api.src.models.membership import OrganizationMembership
from apps.api.src.models.project import Project


@pytest.mark.asyncio
async def test_database_model_creation_and_cascade(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    # 1. Create User
    user = await create_test_user(email="cascade@unotusk.io")

    # 2. Create Org and Membership
    org, membership = await create_test_org(user=user, name="Cascade Corp")

    # 3. Create Project
    project = await create_test_project(organization=org, name="Cascade Project")

    # 4. Create Integration
    integration = Integration(
        id=uuid.uuid4(),
        project_id=project.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.PENDING,
        metadata={"repo": "test/repo"},
    )
    db_session.add(integration)
    await db_session.commit()

    # Verify query
    proj_res = await db_session.execute(select(Project).where(Project.id == project.id))
    assert proj_res.scalar_one_or_none() is not None

    # Delete Org -> should cascade delete project, membership, and integration
    await db_session.delete(org)
    await db_session.commit()

    p_check = await db_session.execute(select(Project).where(Project.id == project.id))
    assert p_check.scalar_one_or_none() is None

    m_check = await db_session.execute(
        select(OrganizationMembership).where(OrganizationMembership.id == membership.id)
    )
    assert m_check.scalar_one_or_none() is None

    i_check = await db_session.execute(select(Integration).where(Integration.id == integration.id))
    assert i_check.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_duplicate_project_slug_in_same_org_fails(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
):
    user = await create_test_user(email="slug@unotusk.io")
    org, _ = await create_test_org(user=user)

    p1 = Project(
        id=uuid.uuid4(),
        organization_id=org.id,
        name="Project One",
        slug="same-slug",
        status=ProjectStatus.CREATED,
    )
    db_session.add(p1)
    await db_session.commit()

    p2 = Project(
        id=uuid.uuid4(),
        organization_id=org.id,
        name="Project Two",
        slug="same-slug",
        status=ProjectStatus.CREATED,
    )
    db_session.add(p2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
