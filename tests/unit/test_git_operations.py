import os
import subprocess
import tempfile

import pytest

from apps.api.src.services.git_operations import GitOperationsService


@pytest.fixture
def sample_git_repo():
    """Initializes a real temporary git repository with 2 commits for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Initialize repository
        subprocess.run(["git", "init", "-b", "main"], cwd=tmp_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test Dev"], cwd=tmp_dir, check=True)
        subprocess.run(["git", "config", "user.email", "dev@unotusk.io"], cwd=tmp_dir, check=True)

        # Commit 1
        file1 = os.path.join(tmp_dir, "auth_service.py")
        with open(file1, "w") as f:
            f.write("class AuthService:\n    def login(self): pass\n")
        subprocess.run(["git", "add", "auth_service.py"], cwd=tmp_dir, check=True)
        subprocess.run(["git", "commit", "-m", "feat: initial auth service"], cwd=tmp_dir, check=True)

        # Create a feature branch
        subprocess.run(["git", "checkout", "-b", "feature/jwt-tokens"], cwd=tmp_dir, check=True)
        with open(file1, "a") as f:
            f.write("    def verify_token(self): pass\n")
        subprocess.run(["git", "commit", "-am", "feat: add token verification"], cwd=tmp_dir, check=True)

        yield tmp_dir


@pytest.mark.asyncio
async def test_get_current_branch(sample_git_repo):
    branch = await GitOperationsService.get_current_branch(sample_git_repo)
    assert branch == "feature/jwt-tokens"


@pytest.mark.asyncio
async def test_list_branches(sample_git_repo):
    branches = await GitOperationsService.list_branches(sample_git_repo)
    assert "main" in branches
    assert "feature/jwt-tokens" in branches


@pytest.mark.asyncio
async def test_get_diff(sample_git_repo):
    diff_res = await GitOperationsService.get_diff(sample_git_repo, base_ref="main", head_ref="feature/jwt-tokens")
    assert diff_res["success"] is True
    assert "verify_token" in diff_res["diff"]
    assert len(diff_res["files_changed"]) == 1
    assert diff_res["files_changed"][0]["path"] == "auth_service.py"
    assert diff_res["files_changed"][0]["insertions"] == 1


@pytest.mark.asyncio
async def test_get_commit_log(sample_git_repo):
    logs = await GitOperationsService.get_commit_log(sample_git_repo, max_count=5)
    assert len(logs) == 2
    assert "add token verification" in logs[0]["message"]
    assert "initial auth service" in logs[1]["message"]
    assert logs[0]["author_name"] == "Test Dev"


@pytest.mark.asyncio
async def test_get_merge_base(sample_git_repo):
    merge_base = await GitOperationsService.get_merge_base(sample_git_repo, "main", "feature/jwt-tokens")
    assert merge_base is not None
    assert len(merge_base) == 40


@pytest.mark.asyncio
async def test_get_file_content_at_commit(sample_git_repo):
    logs = await GitOperationsService.get_commit_log(sample_git_repo, max_count=2)
    initial_sha = logs[1]["sha"]

    # At initial commit, verify_token did not exist
    initial_content = await GitOperationsService.get_file_content_at_commit(sample_git_repo, initial_sha, "auth_service.py")
    assert initial_content is not None
    assert "def login" in initial_content
    assert "def verify_token" not in initial_content
