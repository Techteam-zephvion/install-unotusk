import os
import subprocess
from typing import Any

import httpx

from apps.api.src.api.exceptions import BadRequestException, UnauthorizedException

GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("GITHUB_TOKEN")

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Unotusk-MVP/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def verify_token(self) -> dict[str, Any]:
        """Verify GitHub authentication token and return user profile details."""
        if not self.token:
            raise UnauthorizedException(
                code="GITHUB_TOKEN_REQUIRED",
                message="GitHub token is required to connect repository",
            )

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{GITHUB_API_BASE}/user", headers=self._get_headers())
            if response.status_code == 401:
                raise UnauthorizedException(
                    code="INVALID_GITHUB_TOKEN",
                    message="The provided GitHub token is invalid or expired",
                )
            if response.status_code != 200:
                raise BadRequestException(
                    code="GITHUB_API_ERROR",
                    message=f"GitHub API returned error {response.status_code}",
                )
            return response.json()

    async def list_repositories(self) -> list[dict[str, Any]]:
        """List repositories accessible to the token."""
        headers = self._get_headers()
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/user/repos?per_page=100&sort=updated",
                headers=headers,
            )
            if response.status_code != 200:
                # If unauthenticated, fallback to empty list or error
                if response.status_code == 401:
                    raise UnauthorizedException(
                        code="INVALID_GITHUB_TOKEN",
                        message="Invalid GitHub credentials",
                    )
                return []

            repos = response.json()
            return [
                {
                    "id": str(r["id"]),
                    "name": r["name"],
                    "full_name": r["full_name"],
                    "owner": r["owner"]["login"],
                    "default_branch": r.get("default_branch", "main"),
                    "url": r["html_url"],
                    "clone_url": r["clone_url"],
                    "is_private": r.get("private", False),
                    "description": r.get("description"),
                }
                for r in repos
            ]

    async def get_repository_info(self, owner: str, repo: str) -> dict[str, Any]:
        """Get repository metadata for owner/repo."""
        headers = self._get_headers()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}",
                headers=headers,
            )
            if response.status_code != 200:
                raise BadRequestException(
                    code="REPOSITORY_NOT_FOUND",
                    message=f"Repository {owner}/{repo} not found on GitHub",
                )
            r = response.json()
            return {
                "id": str(r["id"]),
                "name": r["name"],
                "full_name": r["full_name"],
                "owner": r["owner"]["login"],
                "default_branch": r.get("default_branch", "main"),
                "url": r["html_url"],
                "clone_url": r["clone_url"],
                "is_private": r.get("private", False),
                "description": r.get("description"),
            }

    def clone_repository(
        self,
        clone_url: str,
        target_dir: str,
        branch: str | None = None,
    ) -> str:
        """Perform shallow git clone into target_dir and return latest commit SHA."""
        # Inject token if available
        auth_url = clone_url
        if self.token and "github.com" in clone_url:
            auth_url = clone_url.replace("https://", f"https://x-access-token:{self.token}@")

        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd.extend(["-b", branch])
        cmd.extend([auth_url, target_dir])

        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if res.returncode != 0:
            # Mask token in error message if present
            clean_err = res.stderr.replace(self.token or "", "[REDACTED]")
            raise RuntimeError(f"Git clone failed: {clean_err.strip()}")

        # Extract commit sha
        sha_res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return sha_res.stdout.strip() if sha_res.returncode == 0 else "unknown"
