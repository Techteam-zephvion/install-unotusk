import logging
import re
import uuid
from collections.abc import Callable

import httpx
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select

from apps.api.src.auth.security import decode_access_token
from apps.api.src.config.settings import settings
from apps.api.src.core.federation import mint_federation_token
from apps.api.src.db.session import AsyncSessionLocal
from apps.api.src.models.enums import MembershipRole
from apps.api.src.models.membership import (
    OrganizationMembership,
    ProjectMembership,
)
from apps.api.src.models.project import Project
from apps.api.src.models.user import User
from apps.api.src.services.project_service import ProjectService

logger = logging.getLogger("unotusk.gateway")

DATA_PLANE_SUBPATHS = frozenset({
    "ask",
    "conversations",
    "spec",
    "files",
    "symbols",
    "dependencies",
    "repositories",
    "repository",
    "discover",
    "findings",
    "reports",
    "knowledge",
    "services",
})

GATEWAY_PROJECT_REGEX = re.compile(
    r"^(/api/v1)?/projects/([^/?#]+)/([^/?#]+)(?:/(.*))?$"
)


def _candidate_data_plane_hosts() -> list[str]:
    # Order candidate hosts so both bare-metal and Docker bridge deployments connect
    hosts: list[str] = []
    for h in (
        settings.DATA_PLANE_HOST,
        "host.docker.internal",
        "172.17.0.1",
        "127.0.0.1",
    ):
        if h and h.strip() and h.strip() not in hosts:
            hosts.append(h.strip())
    return hosts


class DataPlaneGatewayMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if settings.is_data_plane:
            return await call_next(request)

        match = GATEWAY_PROJECT_REGEX.match(request.url.path)
        if not match:
            return await call_next(request)

        api_prefix, project_ref, sub_root, tail = match.groups()
        if sub_root.lower() not in DATA_PLANE_SUBPATHS:
            return await call_next(request)

        if AsyncSessionLocal is None:
            return await call_next(request)

        # Steps 1-3 execute inside the DB session, then immediately release the connection!
        async with AsyncSessionLocal() as session:
            try:
                resolved_id = await ProjectService.resolve_project_id(
                    session, project_ref
                )
            except Exception:
                return await call_next(request)

            project = await session.get(Project, resolved_id)
            if not project or not project.port or project.port == settings.PORT:
                return await call_next(request)

            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"error": {"code": "MISSING_TOKEN"}},
                )

            raw_jwt = auth_header.removeprefix("Bearer ").strip()
            payload = decode_access_token(raw_jwt)
            if not payload or "sub" not in payload:
                return JSONResponse(
                    status_code=401,
                    content={"error": {"code": "INVALID_TOKEN"}},
                )

            try:
                user_uuid = uuid.UUID(payload["sub"])
            except (ValueError, TypeError):
                return JSONResponse(
                    status_code=401,
                    content={"error": {"code": "INVALID_TOKEN"}},
                )

            user = await session.get(User, user_uuid)
            if user is None:
                return JSONResponse(
                    status_code=401,
                    content={"error": {"code": "USER_NOT_FOUND"}},
                )

            org_q = select(OrganizationMembership).where(
                OrganizationMembership.organization_id == project.organization_id,
                OrganizationMembership.user_id == user.id,
            )
            org_mem = (await session.execute(org_q)).scalar_one_or_none()
            if org_mem is None:
                return JSONResponse(
                    status_code=403,
                    content={"error": {"code": "ORGANIZATION_ACCESS_DENIED"}},
                )

            proj_q = select(ProjectMembership).where(
                ProjectMembership.project_id == project.id,
                ProjectMembership.user_id == user.id,
            )
            proj_mem = (await session.execute(proj_q)).scalar_one_or_none()
            if org_mem.role == MembershipRole.MEMBER and proj_mem is None:
                return JSONResponse(
                    status_code=403,
                    content={"error": {"code": "PROJECT_ACCESS_DENIED"}},
                )

            role_str = (proj_mem.role if proj_mem else org_mem.role).value
            canonical_proj_id = project.id
            target_port = project.port

            fed_token = mint_federation_token(
                user_id=user.id,
                email=user.email,
                name=user.name,
                org_id=project.organization_id,
                project_id=canonical_proj_id,
                project_slug=project.slug,
                role=role_str,
            )

        # <-- DB Session is now closed and returned to SQLAlchemy pool!
        # 4. Proxy Request to Data Plane Container outside the DB session
        prefix_str = api_prefix or ""
        tail_str = f"/{tail}" if tail else ""
        target_path = (
            f"{prefix_str}/projects/{project.slug}/{sub_root}{tail_str}"
        )
        query_str = f"?{request.url.query}" if request.url.query else ""
        skip_req_hdrs = ("host", "content-length", "transfer-encoding")
        forward_headers = {
            k: v
            for k, v in request.headers.items()
            if k.lower() not in skip_req_hdrs
        }
        forward_headers["X-Unotusk-Federation-Token"] = fed_token
        body_bytes = await request.body()

        last_exc: Exception | None = None
        async with httpx.AsyncClient(timeout=120.0) as client:
            for candidate_host in _candidate_data_plane_hosts():
                target_url = (
                    f"http://{candidate_host}:{target_port}"
                    f"{target_path}{query_str}"
                )
                try:
                    dp_resp = await client.request(
                        method=request.method,
                        url=target_url,
                        headers=forward_headers,
                        content=body_bytes,
                    )
                    skip_resp = (
                        "content-encoding",
                        "content-length",
                        "transfer-encoding",
                    )
                    resp_headers = {
                        k: v
                        for k, v in dp_resp.headers.items()
                        if k.lower() not in skip_resp
                    }
                    resp_headers["X-Data-Plane-Proxied"] = "true"
                    resp_headers["X-Data-Plane-Target-Port"] = str(target_port)
                    return Response(
                        content=dp_resp.content,
                        status_code=dp_resp.status_code,
                        headers=resp_headers,
                    )
                except httpx.ConnectError as exc:
                    last_exc = exc
                    continue
                except httpx.RequestError as exc:
                    last_exc = exc
                    break

        logger.error(
            "Data Plane unreachable on port %s across candidate hosts: %s",
            target_port,
            last_exc,
        )
        return JSONResponse(
            status_code=503,
            content={"error": {"code": "DATA_PLANE_UNREACHABLE"}},
        )
