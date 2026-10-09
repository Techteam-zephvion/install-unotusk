import asyncio
import os
import shutil
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

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.request(method, url, headers=self._get_headers(), **kwargs)

                    if response.status_code in (403, 429):
                        # Rate limit check
                        remaining = response.headers.get("x-ratelimit-remaining")
                        if remaining == "0" or response.status_code == 429:
                            raise BadRequestException(
                                code="RATE_LIMIT_EXCEEDED",
                                message="GitHub API rate limit exceeded",
                            )

                    if response.status_code in (500, 502, 503, 504) and attempt < max_retries - 1:
                        await asyncio.sleep(base_delay * (2 ** attempt))
                        continue

                    return response
            except (httpx.RequestError, httpx.TimeoutException) as e:
                if attempt == max_retries - 1:
                    raise BadRequestException(
                        code="GITHUB_NETWORK_ERROR",
                        message=f"Network error communicating with GitHub: {str(e)}",
                    ) from e
                await asyncio.sleep(base_delay * (2 ** attempt))

    async def verify_token(self) -> dict[str, Any]:
        """Verify GitHub authentication token and return user profile details."""
        if not self.token:
            raise UnauthorizedException(
                code="GITHUB_TOKEN_REQUIRED",
                message="GitHub token is required to connect repository",
            )

        response = await self._request_with_retry("GET", f"{GITHUB_API_BASE}/user")
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
        """List repositories accessible to the token with pagination support."""
        url = f"{GITHUB_API_BASE}/user/repos?per_page=100&sort=updated"
        all_repos = []

        while url:
            response = await self._request_with_retry("GET", url)

            if response.status_code != 200:
                if response.status_code == 401:
                    raise UnauthorizedException(
                        code="INVALID_GITHUB_TOKEN",
                        message="Invalid GitHub credentials",
                    )
                return []

            repos = response.json()
            all_repos.extend([
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
            ])

            # Check Link header for pagination
            link_header = response.headers.get("link", "")
            next_url = None
            if link_header:
                links = link_header.split(",")
                for link in links:
                    parts = link.split(";")
                    if len(parts) == 2 and 'rel="next"' in parts[1]:
                        next_url = parts[0].strip()[1:-1]
                        break
            url = next_url

        return all_repos

    async def get_repository_info(self, owner: str, repo: str) -> dict[str, Any]:
        """Get repository metadata for owner/repo."""
        response = await self._request_with_retry("GET", f"{GITHUB_API_BASE}/repos/{owner}/{repo}")
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
        """Perform full git clone into target_dir, fetch PRs, and return latest commit SHA."""
        cmd = ["git", "clone"]
        if branch:
            cmd.extend(["-b", branch])

        if self.token and "github.com" in clone_url:
            cmd.extend(["-c", f"http.extraHeader=Authorization: Bearer {self.token}"])

        cmd.extend([clone_url, target_dir])

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if res.returncode != 0:
                clean_err = res.stderr.replace(self.token or "", "[REDACTED]")
                raise RuntimeError(f"Git clone failed: {clean_err.strip()}")

            # Fetch PRs
            fetch_cmd = ["git", "fetch", "origin", "+refs/pull/*/head:refs/remotes/origin/pr/*"]
            if self.token and "github.com" in clone_url:
                fetch_cmd = ["git", "-c", f"http.extraHeader=Authorization: Bearer {self.token}"] + fetch_cmd[1:]

            subprocess.run(
                fetch_cmd,
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=300,
            )

            # Extract commit sha
            sha_res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return sha_res.stdout.strip() if sha_res.returncode == 0 else "unknown"
        except Exception as e:
            shutil.rmtree(target_dir, ignore_errors=True)
            if isinstance(e, subprocess.TimeoutExpired):
                raise RuntimeError("Git clone timed out") from None
            raise

