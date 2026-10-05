import logging
import re
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from apps.api.src.config.settings import settings

logger = logging.getLogger("unotusk.data_plane")

# Regex to capture project ID in routes like:
# /projects/{project_id} or /api/v1/projects/{project_id}/...
PROJECT_PATH_REGEX = re.compile(
    r"^(?:/api/v1)?/projects/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(?:/.*)?$"
)

# Regex to detect DELETE /projects/{project_id} specifically (not sub-resources)
PROJECT_DELETE_REGEX = re.compile(
    r"^(?:/api/v1)?/projects/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})/?$"
)


class DataPlaneSecurityMiddleware(BaseHTTPMiddleware):
    """
    Container-level authorization guardrails for Unotusk Data Plane instances.

    When an API container is running as a dedicated Data Plane (DATA_PLANE_PROJECT_ID is set):
    1. Cross-Project Boundary Isolation: Blocks any request targeting a project other than
       the assigned DATA_PLANE_PROJECT_ID with 403 DATA_PLANE_BOUNDARY_VIOLATION.
    2. Control Plane Lockdown: Blocks control-plane operations (creating projects, deleting
       projects, managing organizations, or creating accounts) with 403 CONTROL_PLANE_OPERATION_PROHIBITED.
    3. Diagnostic Headers: Injects X-Data-Plane: true and X-Data-Plane-Project-Id headers
       on all responses for auditability and verification.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # If not running in Data Plane mode, behave as standard Control Plane
        if not settings.is_data_plane:
            response = await call_next(request)
            response.headers["X-Data-Plane"] = "false"
            return response

        path = request.url.path
        method = request.method.upper()
        configured_proj_id = str(settings.DATA_PLANE_PROJECT_ID).lower()

        # 1. Allow health endpoints and API documentation without restrictions
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

        # 2. Control Plane Route Lockdown
        # Prohibit creating new projects on a dedicated Data Plane instance
        if method == "POST" and path in ("/projects", f"{settings.API_V1_PREFIX}/projects"):
            logger.warning(
                "Data plane container %s rejected prohibited project creation attempt.",
                configured_proj_id,
            )
            return self._build_control_plane_prohibited_response(path, method)

        # Prohibit deleting a project on a dedicated Data Plane instance
        if method == "DELETE" and PROJECT_DELETE_REGEX.match(path):
            logger.warning(
                "Data plane container %s rejected prohibited project deletion attempt.",
                configured_proj_id,
            )
            return self._build_control_plane_prohibited_response(path, method)

        # Prohibit organization administration on a dedicated Data Plane instance
        if path.startswith("/organizations") or path.startswith(f"{settings.API_V1_PREFIX}/organizations"):
            logger.warning(
                "Data plane container %s rejected prohibited organization operation: %s %s",
                configured_proj_id,
                method,
                path,
            )
            return self._build_control_plane_prohibited_response(path, method)

        # Prohibit account signup on a dedicated Data Plane instance (must be done on Control Plane)
        if path.startswith("/auth/signup") or path.startswith(f"{settings.API_V1_PREFIX}/auth/signup"):
            logger.warning(
                "Data plane container %s rejected prohibited signup operation.",
                configured_proj_id,
            )
            return self._build_control_plane_prohibited_response(path, method)

        # 3. Cross-Project Boundary Isolation
        proj_match = PROJECT_PATH_REGEX.match(path)
        if proj_match:
            requested_id = proj_match.group(1).lower()
            if requested_id != configured_proj_id:
                logger.warning(
                    "DATA_PLANE_BOUNDARY_VIOLATION: Container %s rejected access to project %s on %s %s",
                    configured_proj_id,
                    requested_id,
                    method,
                    path,
                )
                headers = {"X-Data-Plane": "true", "X-Data-Plane-Project-Id": configured_proj_id}
                if settings.DATA_PLANE_ORG_ID:
                    headers["X-Data-Plane-Org-Id"] = str(settings.DATA_PLANE_ORG_ID)

                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "DATA_PLANE_BOUNDARY_VIOLATION",
                            "message": (
                                "Cross-project access is strictly prohibited on dedicated data plane containers."
                            ),
                            "details": {
                                "requested_project_id": requested_id,
                                "data_plane_project_id": configured_proj_id,
                            },
                        }
                    },
                    headers=headers,
                )

        # 4. Process Request and Inject Security Response Headers
        response = await call_next(request)
        self._inject_data_plane_headers(response)
        return response

    def _inject_data_plane_headers(self, response: Response) -> None:
        response.headers["X-Data-Plane"] = "true"
        response.headers["X-Data-Plane-Project-Id"] = str(settings.DATA_PLANE_PROJECT_ID)
        if settings.DATA_PLANE_ORG_ID:
            response.headers["X-Data-Plane-Org-Id"] = str(settings.DATA_PLANE_ORG_ID)

    def _build_control_plane_prohibited_response(self, path: str, method: str) -> JSONResponse:
        configured_proj_id = str(settings.DATA_PLANE_PROJECT_ID)
        headers = {"X-Data-Plane": "true", "X-Data-Plane-Project-Id": configured_proj_id}
        if settings.DATA_PLANE_ORG_ID:
            headers["X-Data-Plane-Org-Id"] = str(settings.DATA_PLANE_ORG_ID)

        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "code": "CONTROL_PLANE_OPERATION_PROHIBITED",
                    "message": (
                        "Control plane operations are not permitted on a dedicated data plane instance."
                    ),
                    "details": {
                        "endpoint": path,
                        "method": method,
                        "data_plane_project_id": configured_proj_id,
                    },
                }
            },
            headers=headers,
        )
