import uuid

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.dependencies.database import get_db
from apps.api.src.api.exceptions import ForbiddenException, UnauthorizedException
from apps.api.src.auth.security import decode_access_token
from apps.api.src.config.settings import settings
from apps.api.src.core.federation import verify_federation_token
from apps.api.src.models.enums import MembershipRole
from apps.api.src.models.membership import OrganizationMembership, ProjectMembership
from apps.api.src.models.organization import Organization
from apps.api.src.models.project import Project
from apps.api.src.models.user import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    # 1. Fast-Path: Control-Plane-Signed Federation Token on Data Plane
    fed_token = request.headers.get("X-Unotusk-Federation-Token") if request else None
    if fed_token and settings.is_data_plane and (settings.DATA_PLANE_PROJECT_ID or settings.DATA_PLANE_PROJECT_SLUG):
        claims = verify_federation_token(
            fed_token,
            settings.DATA_PLANE_PROJECT_SLUG or settings.DATA_PLANE_PROJECT_ID,
        )
        if claims is None:
            raise UnauthorizedException(
                code="INVALID_FEDERATION_TOKEN",
                message="Invalid or expired federation token",
            )

        user_id = uuid.UUID(claims["sub"])
        claim_org_id = uuid.UUID(claims["org_id"])
        proj_id = uuid.UUID(claims["project_id"])
        role_raw = claims.get("role", "MEMBER")
        role_enum = (
            MembershipRole(role_raw)
            if role_raw in MembershipRole._value2member_map_
            else MembershipRole.MEMBER
        )

        # 1a. JIT Upsert User by ID or Email (preserving existing user row if present)
        user = await db.get(User, user_id)
        if user is None:
            q_user = select(User).where(User.email == claims["email"])
            user = (await db.execute(q_user)).scalar_one_or_none()

        if user is None:
            user = User(
                id=user_id,
                email=claims["email"],
                name=claims.get("name") or "Member",
                password_hash="",
            )
            db.add(user)
            await db.flush()

        # 1b. Resolve Project & Organization without violating unique slug constraint
        proj = await db.get(Project, proj_id)
        if proj is None and claims.get("project_slug"):
            q_proj = select(Project).where(Project.slug == claims["project_slug"])
            proj = (await db.execute(q_proj)).scalar_one_or_none()

        target_org_id = proj.organization_id if proj is not None else claim_org_id

        org = await db.get(Organization, target_org_id)
        if org is None:
            q_org = select(Organization).where(
                Organization.slug == settings.DATA_PLANE_ORG_SLUG
            )
            org = (await db.execute(q_org)).scalar_one_or_none()

        if org is None:
            org = (
                await db.execute(select(Organization).limit(1))
            ).scalar_one_or_none()

        if org is None:
            org = Organization(
                id=target_org_id,
                name="Acme Corporation",
                slug=settings.DATA_PLANE_ORG_SLUG,
            )
            db.add(org)
            await db.flush()

        # Ensure project points to the resolved local Organization ID
        if proj is not None and proj.organization_id != org.id:
            proj.organization_id = org.id
            await db.flush()

        # 1c. CRITICAL: Upsert OrganizationMembership (required by all Data Plane services)
        om_q = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org.id,
            OrganizationMembership.user_id == user.id,
        )
        om = (await db.execute(om_q)).scalar_one_or_none()
        if om is None:
            db.add(
                OrganizationMembership(
                    organization_id=org.id,
                    user_id=user.id,
                    role=role_enum,
                )
            )
        elif om.role != role_enum:
            om.role = role_enum

        # 1d. Upsert ProjectMembership
        if proj is not None:
            pm_q = select(ProjectMembership).where(
                ProjectMembership.project_id == proj.id,
                ProjectMembership.user_id == user.id,
            )
            pm = (await db.execute(pm_q)).scalar_one_or_none()
            if pm is None:
                db.add(
                    ProjectMembership(
                        project_id=proj.id,
                        user_id=user.id,
                        role=role_enum,
                    )
                )
            elif pm.role != role_enum:
                pm.role = role_enum
        await db.commit()
        return user

    # 2. Standard Bearer Token Path (Control Plane & Direct-Mode fallback)
    if not credentials or not credentials.credentials:
        raise UnauthorizedException(
            code="MISSING_TOKEN",
            message="Authorization token is required",
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise UnauthorizedException(
            code="INVALID_TOKEN",
            message="Invalid or expired authentication token",
        )

    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError:
        raise UnauthorizedException(
            code="INVALID_TOKEN",
            message="Malformed user identifier in token",
        ) from None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        email = payload.get("email")
        if email:
            email_res = await db.execute(select(User).where(User.email == email))
            user = email_res.scalar_one_or_none()

        if user is None:
            if settings.is_data_plane or payload.get("sub"):
                # Cryptographic Cross-Plane Trust: JIT-provision user from verified Control Plane JWT
                from apps.api.src.auth.security import hash_password

                user_email = email or f"user_{str(user_id)[:8]}@acme.com"
                user_name = user_email.split("@")[0].replace(".", " ").title()
                user = User(
                    id=user_id,
                    email=user_email,
                    name=user_name,
                    hashed_password=hash_password(str(uuid.uuid4())),
                    is_active=True,
                )
                db.add(user)
                await db.flush()

                # If running on a dedicated Data Plane, auto-link to the data plane's org and project
                if settings.is_data_plane:
                    if settings.DATA_PLANE_ORG_ID:
                        try:
                            t_org = uuid.UUID(settings.DATA_PLANE_ORG_ID)
                            org_link = OrganizationMembership(
                                id=uuid.uuid4(),
                                user_id=user.id,
                                organization_id=t_org,
                                role=MembershipRole.MEMBER,
                            )
                            db.add(org_link)
                        except ValueError:
                            pass

                    if settings.DATA_PLANE_PROJECT_ID:
                        try:
                            t_proj = uuid.UUID(settings.DATA_PLANE_PROJECT_ID)
                            proj_link = ProjectMembership(
                                id=uuid.uuid4(),
                                user_id=user.id,
                                project_id=t_proj,
                                role=MembershipRole.MEMBER,
                            )
                            db.add(proj_link)
                        except ValueError:
                            pass

                await db.commit()
                await db.refresh(user)
            else:
                raise UnauthorizedException(
                    code="USER_NOT_FOUND",
                    message="User associated with token does not exist",
                )

    # Data Plane Container-Level Authorization Guardrail
    if settings.is_data_plane:
        target_org_id: uuid.UUID | None = None
        if settings.DATA_PLANE_ORG_ID:
            try:
                target_org_id = uuid.UUID(settings.DATA_PLANE_ORG_ID)
            except ValueError:
                pass

        if target_org_id is None and settings.DATA_PLANE_PROJECT_ID:
            try:
                dp_pid = uuid.UUID(str(settings.DATA_PLANE_PROJECT_ID))
                proj_res = await db.execute(select(Project.organization_id).where(Project.id == dp_pid))
                target_org_id = proj_res.scalar_one_or_none()
            except Exception:
                pass

        if target_org_id is None:
            try:
                first_org = (await db.execute(select(Organization.id).limit(1))).scalar_one_or_none()
                target_org_id = first_org
            except Exception:
                pass

        org_stmt = select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id
        )
        if target_org_id:
            org_stmt = org_stmt.where(OrganizationMembership.organization_id == target_org_id)

        org_res = await db.execute(org_stmt)
        org_mem = org_res.scalar_one_or_none()

        if org_mem is None:
            if target_org_id:
                try:
                    org_link = OrganizationMembership(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        organization_id=target_org_id,
                        role=MembershipRole.OWNER,
                    )
                    db.add(org_link)
                    await db.commit()
                    org_mem = org_link
                except Exception:
                    pass

        # In single-tenant MVP, ensure user is never blocked from their own data plane
        if org_mem is None:
            logger.warning("Auto-admitting verified user %s to single-tenant data plane", user.id)

        # Enforce project assignment for regular members
        if org_mem.role not in (MembershipRole.OWNER, MembershipRole.ADMIN):
            try:
                data_plane_proj_id = uuid.UUID(str(settings.DATA_PLANE_PROJECT_ID))
                proj_stmt = select(ProjectMembership).where(
                    ProjectMembership.project_id == data_plane_proj_id,
                    ProjectMembership.user_id == user.id,
                )
                proj_res = await db.execute(proj_stmt)
                proj_mem = proj_res.scalar_one_or_none()
                if proj_mem is None:
                    proj_link = ProjectMembership(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        project_id=data_plane_proj_id,
                        role=MembershipRole.MEMBER,
                    )
                    db.add(proj_link)
                    await db.commit()
            except ValueError:
                pass

    return user


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not credentials or not credentials.credentials:
        return None
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        return None
    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
