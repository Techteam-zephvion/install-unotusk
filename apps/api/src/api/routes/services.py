import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.dependencies.auth import get_current_user
from apps.api.src.api.dependencies.database import get_db
from apps.api.src.models.user import User
from apps.api.src.schemas.service import (
    ServiceCreate,
    ServiceRead,
    ServiceUpdate,
)
from apps.api.src.services.service_service import ServiceService

router = APIRouter(prefix="/projects/{project_id}/services", tags=["Service Ontology"])


@router.get("", response_model=list[ServiceRead])
async def list_services(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ServiceRead]:
    return await ServiceService.list_services(db, current_user.id, project_id)


@router.post("", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
async def create_service(
    project_id: uuid.UUID,
    data: ServiceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ServiceRead:
    return await ServiceService.create_service(db, current_user.id, project_id, data)


@router.get("/{service_id}", response_model=ServiceRead)
async def get_service(
    project_id: uuid.UUID,
    service_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ServiceRead:
    return await ServiceService.get_service(db, current_user.id, project_id, service_id)


@router.patch("/{service_id}", response_model=ServiceRead)
async def update_service(
    project_id: uuid.UUID,
    service_id: uuid.UUID,
    data: ServiceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ServiceRead:
    return await ServiceService.update_service(db, current_user.id, project_id, service_id, data)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    project_id: uuid.UUID,
    service_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await ServiceService.delete_service(db, current_user.id, project_id, service_id)


@router.post("/{service_id}/repositories/{repository_id}", response_model=ServiceRead)
async def associate_repository(
    project_id: uuid.UUID,
    service_id: uuid.UUID,
    repository_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ServiceRead:
    return await ServiceService.associate_repository(
        db, current_user.id, project_id, service_id, repository_id
    )


@router.delete("/{service_id}/repositories/{repository_id}", response_model=ServiceRead)
async def dissociate_repository(
    project_id: uuid.UUID,
    service_id: uuid.UUID,
    repository_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ServiceRead:
    return await ServiceService.dissociate_repository(
        db, current_user.id, project_id, service_id, repository_id
    )
