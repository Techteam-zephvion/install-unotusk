from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

logger = logging.getLogger("unotusk-git-operations")


class GitOperationsService:
    """
    Executes real Git CLI operations directly on repository clones.
    Provides diffs, commit histories, merge-base calculations, branch management,
    and commit-level file inspection.
    """

    @staticmethod
    async def _run_git_command(args: list[str], cwd: str, timeout: float = 15.0) -> tuple[int, str, str]:
        """Runs a git command asynchronously in the specified working directory."""
        if not os.path.exists(cwd):
            return 1, "", f"Directory does not exist: {cwd}"

        try:
            proc = await asyncio.create_subprocess_exec(
                "git",
                *args,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return (
                proc.returncode if proc.returncode is not None else 1,
                stdout_b.decode("utf-8", errors="replace"),
                stderr_b.decode("utf-8", errors="replace"),
            )
        except TimeoutError:
            return 1, "", f"Git command timed out after {timeout}s: git {' '.join(args)}"
        except Exception as exc:
            return 1, "", str(exc)

    @classmethod
    async def get_current_branch(cls, repo_dir: str) -> str:
        code, stdout, _ = await cls._run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir)
        if code == 0 and stdout.strip():
            return stdout.strip()
        return "main"

    @classmethod
    async def list_branches(cls, repo_dir: str) -> list[str]:
        code, stdout, _ = await cls._run_git_command(["branch", "-a", "--format=%(refname:short)"], cwd=repo_dir)
        if code != 0 or not stdout.strip():
            return ["main"]

        branches: list[str] = []
        for line in stdout.strip().splitlines():
            b = line.strip().replace("origin/", "")
            if b and "HEAD" not in b and b not in branches:
                branches.append(b)
        return branches or ["main"]

    @classmethod
    async def get_diff(
        cls,
        repo_dir: str,
        base_ref: str,
        head_ref: str = "HEAD",
        paths: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Executes `git diff <base_ref>..<head_ref>` and returns the raw patch,
        as well as file-level change statistics.
        """
        diff_args = ["diff", f"{base_ref}..{head_ref}"]
        if paths:
            diff_args.append("--")
            diff_args.extend(paths)

        code, stdout, stderr = await cls._run_git_command(diff_args, cwd=repo_dir)
        if code != 0:
            return {
                "success": False,
                "error": stderr.strip() or "Failed to compute git diff",
                "diff": "",
                "files_changed": [],
            }

        # Also get shortstat summary
        stat_args = ["diff", "--numstat", f"{base_ref}..{head_ref}"]
        _, stat_stdout, _ = await cls._run_git_command(stat_args, cwd=repo_dir)

        files_changed = []
        for line in stat_stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                files_changed.append({
                    "insertions": int(parts[0]) if parts[0].isdigit() else 0,
                    "deletions": int(parts[1]) if parts[1].isdigit() else 0,
                    "path": parts[2].strip(),
                })

        return {
            "success": True,
            "base_ref": base_ref,
            "head_ref": head_ref,
            "diff": stdout,
            "files_changed": files_changed,
            "total_files": len(files_changed),
        }

    @classmethod
    async def get_commit_log(
        cls,
        repo_dir: str,
        max_count: int = 20,
        branch: str = "HEAD",
    ) -> list[dict[str, Any]]:
        """
        Retrieves the structured commit log from the repository using format unit separators.
        """
        log_args = [
            "log",
            f"-{max_count}",
            "--format=%H%x1f%s%x1f%an%x1f%ae%x1f%cI%x1f%P",
            branch,
        ]
        code, stdout, _ = await cls._run_git_command(log_args, cwd=repo_dir)
        if code != 0 or not stdout.strip():
            return []

        commits: list[dict[str, Any]] = []
        for entry in stdout.strip().splitlines():
            parts = entry.split("\x1f")
            if len(parts) >= 5:
                commits.append({
                    "sha": parts[0],
                    "message": parts[1],
                    "author_name": parts[2],
                    "author_email": parts[3],
                    "committed_at": parts[4],
                    "parent_shas": parts[5].split() if len(parts) > 5 and parts[5] else [],
                })
        return commits

    @classmethod
    async def get_merge_base(cls, repo_dir: str, ref1: str, ref2: str) -> str | None:
        """Finds the common ancestor commit of two branches or refs."""
        code, stdout, _ = await cls._run_git_command(["merge-base", ref1, ref2], cwd=repo_dir)
        if code == 0 and stdout.strip():
            return stdout.strip()
        return None

    @classmethod
    async def get_file_content_at_commit(
        cls,
        repo_dir: str,
        commit_sha: str,
        file_path: str,
    ) -> str | None:
        """Retrieves exact file content at a specific historical commit SHA."""
        target = f"{commit_sha}:{file_path}"
        code, stdout, _ = await cls._run_git_command(["show", target], cwd=repo_dir)
        if code == 0:
            return stdout
        return None

    @classmethod
    async def fetch_latest(cls, repo_dir: str) -> bool:
        """Executes `git fetch --all --prune` to refresh remote refs."""
        code, _, _ = await cls._run_git_command(["fetch", "--all", "--prune"], cwd=repo_dir, timeout=30.0)
        return code == 0
