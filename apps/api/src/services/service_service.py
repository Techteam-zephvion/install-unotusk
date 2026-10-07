import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.src.api.exceptions import ConflictException, NotFoundException
from apps.api.src.models.repository import Repository
from apps.api.src.models.service import Service
from apps.api.src.schemas.service import (
    ServiceCreate,
    ServiceRead,
    ServiceUpdate,
)
from apps.api.src.services.repository_service import RepositoryService


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", slug).strip("-_")


class ServiceService:
    @staticmethod
    async def list_services(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> list[ServiceRead]:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        query = (
            select(Service)
            .where(Service.project_id == project.id)
            .options(selectinload(Service.repositories))
            .order_by(Service.name.asc())
        )
        res = await session.execute(query)
        services = res.scalars().all()

        results = []
        for s in services:
            read_obj = ServiceRead(
                id=s.id,
                project_id=s.project_id,
                name=s.name,
                slug=s.slug,
                description=s.description,
                tier=s.tier,
                service_metadata=s.service_metadata or {},
                repository_ids=[r.id for r in s.repositories],
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            results.append(read_obj)
        return results

    @staticmethod
    async def get_service(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        service_id: uuid.UUID,
    ) -> ServiceRead:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        query = (
            select(Service)
            .where(Service.id == service_id, Service.project_id == project.id)
            .options(selectinload(Service.repositories))
        )
        res = await session.execute(query)
        service = res.scalar_one_or_none()
        if service is None:
            raise NotFoundException(code="SERVICE_NOT_FOUND", message="Service not found")

        return ServiceRead(
            id=service.id,
            project_id=service.project_id,
            name=service.name,
            slug=service.slug,
            description=service.description,
            tier=service.tier,
            service_metadata=service.service_metadata or {},
            repository_ids=[r.id for r in service.repositories],
            created_at=service.created_at,
            updated_at=service.updated_at,
        )

    @staticmethod
    async def create_service(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        data: ServiceCreate,
    ) -> ServiceRead:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        slug = data.slug or _slugify(data.name)
        if not slug:
            slug = "service"

        # Check slug conflict
        check_query = select(Service).where(
            Service.project_id == project.id,
            Service.slug == slug,
        )
        existing = await session.execute(check_query)
        if existing.scalar_one_or_none() is not None:
            raise ConflictException(
                code="SERVICE_SLUG_CONFLICT",
                message=f"Service with slug '{slug}' already exists in this project",
            )

        service = Service(
            project_id=project.id,
            name=data.name,
            slug=slug,
            description=data.description,
            tier=data.tier or "tier-1",
            service_metadata=data.service_metadata or {},
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)

        return ServiceRead(
            id=service.id,
            project_id=service.project_id,
            name=service.name,
            slug=service.slug,
            description=service.description,
            tier=service.tier,
            service_metadata=service.service_metadata or {},
            repository_ids=[],
            created_at=service.created_at,
            updated_at=service.updated_at,
        )

    @staticmethod
    async def update_service(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        service_id: uuid.UUID,
        data: ServiceUpdate,
    ) -> ServiceRead:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        query = (
            select(Service)
            .where(Service.id == service_id, Service.project_id == project.id)
            .options(selectinload(Service.repositories))
        )
        res = await session.execute(query)
        service = res.scalar_one_or_none()
        if service is None:
            raise NotFoundException(code="SERVICE_NOT_FOUND", message="Service not found")

        if data.slug is not None and data.slug != service.slug:
            check_query = select(Service).where(
                Service.project_id == project.id,
                Service.slug == data.slug,
                Service.id != service.id,
            )
            existing = await session.execute(check_query)
            if existing.scalar_one_or_none() is not None:
                raise ConflictException(
                    code="SERVICE_SLUG_CONFLICT",
                    message=f"Service with slug '{data.slug}' already exists in this project",
                )
            service.slug = data.slug

        if data.name is not None:
            service.name = data.name
        if data.description is not None:
            service.description = data.description
        if data.tier is not None:
            service.tier = data.tier
        if data.service_metadata is not None:
            service.service_metadata = data.service_metadata

        await session.commit()
        await session.refresh(service)

        return ServiceRead(
            id=service.id,
            project_id=service.project_id,
            name=service.name,
            slug=service.slug,
            description=service.description,
            tier=service.tier,
            service_metadata=service.service_metadata or {},
            repository_ids=[r.id for r in service.repositories],
            created_at=service.created_at,
            updated_at=service.updated_at,
        )

    @staticmethod
    async def delete_service(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        service_id: uuid.UUID,
    ) -> None:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        query = select(Service).where(Service.id == service_id, Service.project_id == project.id)
        res = await session.execute(query)
        service = res.scalar_one_or_none()
        if service is None:
            raise NotFoundException(code="SERVICE_NOT_FOUND", message="Service not found")

        await session.delete(service)
        await session.commit()

    @staticmethod
    async def associate_repository(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        service_id: uuid.UUID,
        repository_id: uuid.UUID,
    ) -> ServiceRead:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        # Verify service exists in project
        service_query = (
            select(Service)
            .where(Service.id == service_id, Service.project_id == project.id)
            .options(selectinload(Service.repositories))
        )
        service_res = await session.execute(service_query)
        service = service_res.scalar_one_or_none()
        if service is None:
            raise NotFoundException(code="SERVICE_NOT_FOUND", message="Service not found")

        # Verify repository exists in project
        repo_query = select(Repository).where(
            Repository.id == repository_id,
            Repository.project_id == project.id,
        )
        repo_res = await session.execute(repo_query)
        repo = repo_res.scalar_one_or_none()
        if repo is None:
            raise NotFoundException(code="REPOSITORY_NOT_FOUND", message="Repository not found")

        repo.service_id = service.id
        await session.commit()

        repos_query = select(Repository.id).where(Repository.service_id == service.id)
        repos_res = await session.execute(repos_query)
        repo_ids = list(repos_res.scalars().all())

        return ServiceRead(
            id=service.id,
            project_id=service.project_id,
            name=service.name,
            slug=service.slug,
            description=service.description,
            tier=service.tier,
            service_metadata=service.service_metadata or {},
            repository_ids=repo_ids,
            created_at=service.created_at,
            updated_at=service.updated_at,
        )

    @staticmethod
    async def dissociate_repository(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        service_id: uuid.UUID,
        repository_id: uuid.UUID,
    ) -> ServiceRead:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        service_query = (
            select(Service)
            .where(Service.id == service_id, Service.project_id == project.id)
        )
        service_res = await session.execute(service_query)
        service = service_res.scalar_one_or_none()
        if service is None:
            raise NotFoundException(code="SERVICE_NOT_FOUND", message="Service not found")

        repo_query = select(Repository).where(
            Repository.id == repository_id,
            Repository.project_id == project.id,
        )
        repo_res = await session.execute(repo_query)
        repo = repo_res.scalar_one_or_none()
        if repo is None:
            raise NotFoundException(code="REPOSITORY_NOT_FOUND", message="Repository not found")

        if repo.service_id == service.id:
            repo.service_id = None
            await session.commit()

        repos_query = select(Repository.id).where(Repository.service_id == service.id)
        repos_res = await session.execute(repos_query)
        repo_ids = list(repos_res.scalars().all())

        return ServiceRead(
            id=service.id,
            project_id=service.project_id,
            name=service.name,
            slug=service.slug,
            description=service.description,
            tier=service.tier,
            service_metadata=service.service_metadata or {},
            repository_ids=repo_ids,
            created_at=service.created_at,
            updated_at=service.updated_at,
        )
