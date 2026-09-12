import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.dependencies.auth import get_current_user
from apps.api.src.api.dependencies.database import get_db
from apps.api.src.models.user import User
from apps.api.src.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from apps.api.src.services.org_service import OrgService
from apps.api.src.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    # Service verifies user membership in data.organization_id
    return await ProjectService.create_project(db, current_user.id, data)


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    organization_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectRead]:
    # If organization_id is not specified, use user's first organization
    target_org_id = organization_id
    if target_org_id is None:
        user_orgs = await OrgService.list_user_organizations(db, current_user.id)
        if not user_orgs:
            return []
        target_org_id = user_orgs[0].id

    # Service verifies user membership in target_org_id
    return await ProjectService.list_projects(db, current_user.id, target_org_id)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    # Service verifies project exists and caller belongs to project's organization
    return await ProjectService.get_project(db, current_user.id, project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    return await ProjectService.update_project(db, current_user.id, project_id, data)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await ProjectService.delete_project(db, current_user.id, project_id)
