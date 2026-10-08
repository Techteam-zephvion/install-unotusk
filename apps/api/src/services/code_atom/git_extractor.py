import logging
import os
import subprocess
from datetime import datetime

from apps.api.src.schemas.code_atom import GitCommitArtifact

logger = logging.getLogger("unotusk-code-atom-git")


def extract_git_commit_artifact(
    repo_dir: str,
    fallback_sha: str | None = None,
) -> GitCommitArtifact | None:
    """
    Extracts commit metadata and unified patch diff from a Git repository directory.

    Returns:
    - GitCommitArtifact if repository contains valid commit history.
    - None if directory is not a git repo or commands fail.
    """
    if not repo_dir or not os.path.exists(repo_dir):
        return None

    # Check if .git exists or directory is inside a work tree
    git_dir = os.path.join(repo_dir, ".git")
    if not os.path.exists(git_dir):
        # Verify via git rev-parse --is-inside-work-tree
        try:
            check_res = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if check_res.returncode != 0:
                return None
        except Exception:
            return None

    try:
        # 1. Extract commit metadata using unit separator delimiter
        log_res = subprocess.run(
            ["git", "log", "-1", '--format=%H%x1f%s%x1f%an%x1f%ae%x1f%cI'],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if log_res.returncode != 0 or not log_res.stdout.strip():
            # If log fails, try rev-parse for fallback
            sha = fallback_sha or "unknown"
            return GitCommitArtifact(
                commit_sha=sha,
                commit_message="Initial import",
                raw_diff="",
            )

        parts = log_res.stdout.strip().split("\x1f")
        commit_sha = parts[0] if len(parts) > 0 and parts[0] else (fallback_sha or "unknown")
        commit_message = parts[1] if len(parts) > 1 else ""
        author_name = parts[2] if len(parts) > 2 and parts[2] else None
        author_email = parts[3] if len(parts) > 3 and parts[3] else None

        committed_at = None
        if len(parts) > 4 and parts[4]:
            try:
                committed_at = datetime.fromisoformat(parts[4])
            except Exception:
                pass

        # 2. Extract patch diff for HEAD
        # Attempt standard git show patch
        show_res = subprocess.run(
            ["git", "show", '--format=', "--patch", "HEAD", "-n", "1"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=20,
        )
        raw_diff = ""
        if show_res.returncode == 0 and show_res.stdout.strip():
            raw_diff = show_res.stdout
        else:
            # Fallback for root commit without parents
            diff_tree_res = subprocess.run(
                ["git", "diff-tree", "-p", "--root", "HEAD"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=20,
            )
            if diff_tree_res.returncode == 0:
                raw_diff = diff_tree_res.stdout

        return GitCommitArtifact(
            commit_sha=commit_sha,
            commit_message=commit_message,
            author_name=author_name,
            author_email=author_email,
            committed_at=committed_at,
            raw_diff=raw_diff,
        )

    except Exception as e:
        logger.warning(f"Failed to extract Git commit artifact from {repo_dir}: {e}")
        return None
