import uuid

import pytest
from pydantic import ValidationError

from apps.api.src.schemas.project import ProjectCreate
from apps.api.src.schemas.user import UserCreate
from apps.api.src.services.slug import slugify


def test_user_create_validation():
    # Valid user creation
    valid = UserCreate(
        name="Alan Turing",
        email="alan@turing.org",
        password="ValidPassword123!",
    )
    assert valid.name == "Alan Turing"
    assert valid.email == "alan@turing.org"

    # Invalid email
    with pytest.raises(ValidationError):
        UserCreate(name="Alan", email="not-an-email", password="ValidPassword123!")

    # Password too short (< 8 chars)
    with pytest.raises(ValidationError):
        UserCreate(name="Alan", email="alan@turing.org", password="short")


def test_project_create_validation():
    org_id = uuid.uuid4()
    project = ProjectCreate(
        organization_id=org_id,
        name="Project Alpha",
        description="A great project",
    )
    assert project.name == "Project Alpha"
    assert project.organization_id == org_id


def test_slugify_utility():
    assert slugify("My Project Name") == "my-project-name"
    assert slugify("  Special   Characters!@#$%^  ") == "special-characters"
    assert slugify("CamelCaseProject") == "camelcaseproject"
    assert len(slugify("")) > 0
