import logging
import os
import subprocess
from datetime import datetime

from apps.api.src.schemas.code_atom import GitCommitArtifact

logger = logging.getLogger("unotusk-code-atom-git")


class InvalidBaseCommitError(ValueError):
    """Raised when the base commit SHA is invalid or not found in the git repository."""

    pass


def extract_git_commit_artifact(
    repo_dir: str,
    fallback_sha: str | None = None,
    commit_ref: str = "HEAD",
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
            ["git", "log", "-1", '--format=%H%x1f%s%x1f%an%x1f%ae%x1f%cI', commit_ref],
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

        # 2. Extract patch diff for commit_ref
        # Attempt standard git show patch
        show_res = subprocess.run(
            ["git", "show", '--format=', "--patch", commit_ref, "-n", "1"],
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
                ["git", "diff-tree", "-p", "--root", commit_ref],
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


def extract_incremental_commit_artifacts(
    repo_dir: str,
    base_commit_sha: str | None = None,
    target_commit_sha: str = "HEAD",
    max_commits: int | None = None,
) -> list[GitCommitArtifact]:
    """
    Extracts GitCommitArtifact list for all commits newer than base_commit_sha up to target_commit_sha
    in topological/chronological order (oldest to newest).

    Behavior:
    - If base_commit_sha is provided:
        - Validates base_commit_sha exists. Raises InvalidBaseCommitError if not found.
        - If base_commit_sha == target_commit_sha: returns [] (safe no-op).
        - Queries commits using `git rev-list --reverse base..target`.
    - If base_commit_sha is None (first-time indexing):
        - Queries commits using `git rev-list --reverse target`.
        - If max_commits is set, limits to that number of commits.
    - If no new commits exist: returns [] (safe no-op).
    - Returns list of GitCommitArtifact with full diffs in chronological order.
    """
    if not repo_dir or not os.path.exists(repo_dir):
        return []

    # Check if .git exists or directory is inside a work tree
    git_dir = os.path.join(repo_dir, ".git")
    if not os.path.exists(git_dir):
        try:
            check_res = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if check_res.returncode != 0:
                return []
        except Exception:
            return []

    # 1. Resolve and validate target_commit_sha
    target_check = subprocess.run(
        ["git", "rev-parse", "--verify", f"{target_commit_sha}^{{commit}}"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if target_check.returncode != 0:
        raise ValueError(
            f"Target commit '{target_commit_sha}' does not exist in repository {repo_dir}"
        )
    resolved_target = target_check.stdout.strip()

    # 2. Resolve and validate base_commit_sha if provided
    if base_commit_sha:
        base_check = subprocess.run(
            ["git", "rev-parse", "--verify", f"{base_commit_sha}^{{commit}}"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if base_check.returncode != 0:
            raise InvalidBaseCommitError(
                f"Base commit '{base_commit_sha}' does not exist in repository {repo_dir}"
            )
        resolved_base = base_check.stdout.strip()

        if resolved_base == resolved_target:
            return []

        rev_args = ["git", "rev-list", "--reverse", f"{resolved_base}..{resolved_target}"]
    else:
        # First-time indexing: all commits leading up to target_commit_sha in chronological order
        rev_args = ["git", "rev-list", "--reverse", resolved_target]
        if max_commits is not None and max_commits > 0:
            rev_args.extend(["-n", str(max_commits)])

    rev_res = subprocess.run(
        rev_args,
        cwd=repo_dir,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if rev_res.returncode != 0:
        logger.warning(
            f"Failed to list commits between {base_commit_sha} and {target_commit_sha}: {rev_res.stderr}"
        )
        return []

    commit_shas = [c.strip() for c in rev_res.stdout.strip().splitlines() if c.strip()]
    if max_commits and len(commit_shas) > max_commits:
        commit_shas = commit_shas[-max_commits:]

    artifacts: list[GitCommitArtifact] = []
    for sha in commit_shas:
        art = extract_git_commit_artifact(repo_dir=repo_dir, fallback_sha=sha, commit_ref=sha)
        if art:
            artifacts.append(art)

    return artifacts
