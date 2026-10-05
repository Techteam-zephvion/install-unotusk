import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from apps.api.src.models.enums import MembershipRole, ProjectStatus
from apps.api.src.schemas.project import (
    ProjectMemberAdd,
    ProjectMemberRead,
    ProjectMemberUpdateRole,
    ProjectRead,
)


def test_project_member_add_validation():
    # 1. Valid with user_id
    u_id = uuid.uuid4()
    pma1 = ProjectMemberAdd(user_id=u_id, role=MembershipRole.ADMIN)
    assert pma1.user_id == u_id
    assert pma1.email is None
    assert pma1.role == MembershipRole.ADMIN

    # 2. Valid with email
    pma2 = ProjectMemberAdd(email="dev@unotusk.io")
    assert pma2.email == "dev@unotusk.io"
    assert pma2.user_id is None
    assert pma2.role == MembershipRole.MEMBER

    # 3. Invalid with neither user_id nor email
    with pytest.raises(ValidationError) as exc_info:
        ProjectMemberAdd()
    assert "Either user_id or email must be provided" in str(exc_info.value)


def test_project_member_read_serialization():
    pm_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    u_id = uuid.uuid4()
    now = datetime.now(UTC)

    pm_read = ProjectMemberRead(
        id=pm_id,
        project_id=proj_id,
        user_id=u_id,
        role=MembershipRole.MEMBER,
        created_at=now,
        user_name="John Doe",
        user_email="john@unotusk.io",
    )
    assert pm_read.id == pm_id
    assert pm_read.user_name == "John Doe"
    assert pm_read.role == MembershipRole.MEMBER


def test_project_member_update_role():
    update = ProjectMemberUpdateRole(role=MembershipRole.ADMIN)
    assert update.role == MembershipRole.ADMIN


def test_project_read_with_role():
    p_id = uuid.uuid4()
    org_id = uuid.uuid4()
    now = datetime.now(UTC)

    p_read = ProjectRead(
        id=p_id,
        organization_id=org_id,
        name="Test",
        slug="test",
        status=ProjectStatus.READY,
        created_at=now,
        updated_at=now,
        role=MembershipRole.ADMIN,
    )
    assert p_read.role == MembershipRole.ADMIN
