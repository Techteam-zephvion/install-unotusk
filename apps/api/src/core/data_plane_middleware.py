import logging
import re
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from apps.api.src.config.settings import settings

logger = logging.getLogger("unotusk.data_plane")

# Captures group(1) = project_ref (UUID or slug), group(2) = optional subpath
PROJECT_ROUTE_REGEX = re.compile(
    r"^(?:/api/v1)?/projects/([^/?#]+)(?:/(.*))?$"
)


class DataPlaneSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.is_data_plane:
            response = await call_next(request)
            response.headers["X-Data-Plane"] = "false"
            return response

        path = request.url.path.rstrip("/") or "/"
        method = request.method.upper()
        allowed_refs = {
            r.strip().lower()
            for r in (
                settings.DATA_PLANE_PROJECT_ID,
                settings.DATA_PLANE_PROJECT_SLUG,
            )
            if r and r.strip()
        }

        fed_token = request.headers.get("X-Unotusk-Federation-Token")
        if fed_token:
            from apps.api.src.core.federation import verify_federation_token
            claims = verify_federation_token(
                fed_token,
                settings.DATA_PLANE_PROJECT_SLUG or settings.DATA_PLANE_PROJECT_ID,
            )
            if claims:
                if claims.get("project_id"):
                    allowed_refs.add(str(claims["project_id"]).strip().lower())
                if claims.get("project_slug"):
                    allowed_refs.add(str(claims["project_slug"]).strip().lower())

        # 1. Permit health and OpenAPI documentation endpoints
        if path in (
            "/health",
            "/health/ready",
            "/docs",
            "/openapi.json",
            "/redoc",
            f"{settings.API_V1_PREFIX}/health",
            f"{settings.API_V1_PREFIX}/health/ready",
        ):
            response = await call_next(request)
            self._inject_data_plane_headers(response)
            return response

        # 2. Control Plane Route Lockdown (projects, sync-servers, orgs, signup)
        if (
            (method == "POST" and path in ("/projects", f"{settings.API_V1_PREFIX}/projects"))
            or path in (
                "/projects/sync-servers",
                f"{settings.API_V1_PREFIX}/projects/sync-servers",
            )
            or path.startswith("/organizations")
            or path.startswith(f"{settings.API_V1_PREFIX}/organizations")
            or path.startswith("/auth/signup")
            or path.startswith(f"{settings.API_V1_PREFIX}/auth/signup")
        ):
            return self._prohibited_response(path, method)

        # 3. Slug- and UUID-Aware Project Boundary Isolation
        match = PROJECT_ROUTE_REGEX.match(path)
        if match:
            requested_ref = match.group(1).strip().lower()
            subpath = (match.group(2) or "").strip("/")

            # 3a. Prohibit root project deletion (DELETE /projects/{ref})
            if method == "DELETE" and not subpath:
                return self._prohibited_response(path, method)

            # 3b. Verify requested_ref matches assigned Data Plane UUID or Slug
            if requested_ref not in allowed_refs:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "DATA_PLANE_BOUNDARY_VIOLATION",
                            "message": "Cross-project access is prohibited.",
                            "details": {
                                "requested_project_id": requested_ref,
                                "requested_project_ref": requested_ref,
                                "assigned_project_id": str(settings.DATA_PLANE_PROJECT_ID or ""),
                                "allowed_refs": sorted(allowed_refs),
                            },
                        }
                    },
                    headers=self._get_headers(),
                )

        response = await call_next(request)
        self._inject_data_plane_headers(response)
        return response

    def _get_headers(self) -> dict[str, str]:
        pid = str(settings.DATA_PLANE_PROJECT_ID or "")
        headers = {"X-Data-Plane": "true", "X-Data-Plane-Project-Id": pid}
        if settings.DATA_PLANE_PROJECT_SLUG:
            slug = str(settings.DATA_PLANE_PROJECT_SLUG)
            headers["X-Data-Plane-Project-Slug"] = slug
        if settings.DATA_PLANE_ORG_ID:
            headers["X-Data-Plane-Org-Id"] = str(settings.DATA_PLANE_ORG_ID)
        return headers

    def _inject_data_plane_headers(self, response: Response) -> None:
        for k, v in self._get_headers().items():
            response.headers[k] = v

    def _prohibited_response(self, path: str, method: str) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "code": "CONTROL_PLANE_OPERATION_PROHIBITED",
                    "message": "Control plane operation prohibited on Data Plane.",
                    "details": {"endpoint": path, "method": method},
                }
            },
            headers=self._get_headers(),
        )
