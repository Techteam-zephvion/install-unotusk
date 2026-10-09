import subprocess
from unittest.mock import MagicMock, patch

import httpx
import pytest

from apps.api.src.api.exceptions import BadRequestException
from apps.api.src.services.github_client import GitHubClient


@pytest.fixture
def github_client():
    return GitHubClient(token="fake-token")

@pytest.mark.asyncio
async def test_verify_token_success(github_client):
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"login": "testuser", "id": 123}
        mock_request.return_value = mock_response

        result = await github_client.verify_token()
        assert result["login"] == "testuser"

@pytest.mark.asyncio
async def test_list_repositories_pagination(github_client):
    with patch("httpx.AsyncClient.request") as mock_request:
        # Mock first response with Link header
        mock_response_1 = MagicMock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = [{"id": 1, "name": "repo1", "full_name": "test/repo1", "owner": {"login": "test"}, "html_url": "url1", "clone_url": "curl1"}]
        mock_response_1.headers = {"link": '<https://api.github.com/user/repos?page=2>; rel="next"'}

        # Mock second response without Link header
        mock_response_2 = MagicMock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = [{"id": 2, "name": "repo2", "full_name": "test/repo2", "owner": {"login": "test"}, "html_url": "url2", "clone_url": "curl2"}]
        mock_response_2.headers = {}

        mock_request.side_effect = [mock_response_1, mock_response_2]

        repos = await github_client.list_repositories()
        assert len(repos) == 2
        assert repos[0]["name"] == "repo1"
        assert repos[1]["name"] == "repo2"
        assert mock_request.call_count == 2

@pytest.mark.asyncio
async def test_retry_on_network_error(github_client):
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_request.side_effect = httpx.TimeoutException("Timeout")

        # Override retry delays for faster test execution
        with patch("asyncio.sleep"):
            with pytest.raises(BadRequestException) as exc:
                await github_client.verify_token()

            assert exc.value.code == "GITHUB_NETWORK_ERROR"
            assert mock_request.call_count == 3

@pytest.mark.asyncio
async def test_rate_limit_handling(github_client):
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {"x-ratelimit-remaining": "0"}
        mock_request.return_value = mock_response

        with pytest.raises(BadRequestException) as exc:
            await github_client.verify_token()

        assert exc.value.code == "RATE_LIMIT_EXCEEDED"

def test_clone_repository_token_masking(github_client):
    with patch("subprocess.run") as mock_run:
        # Mock failure to test masking in error message
        mock_result = MagicMock()
        mock_result.returncode = 128
        mock_result.stderr = "fatal: repository 'https://x-access-token:fake-token@github.com/org/repo' not found"
        mock_run.return_value = mock_result

        with pytest.raises(RuntimeError) as exc:
            github_client.clone_repository("https://github.com/org/repo.git", "/tmp/fake-dir")

        # The fake-token should be redacted in the exception message
        assert "fake-token" not in str(exc.value)
        assert "[REDACTED]" in str(exc.value)

        # Verify that subprocess was called securely with extra headers instead of inline token
        call_args = mock_run.call_args[0][0]
        assert "fake-token" not in call_args[0]
        assert "http.extraHeader=Authorization: Bearer fake-token" in call_args

def test_clone_repository_cleanup_on_failure(github_client):
    with patch("subprocess.run") as mock_run, patch("shutil.rmtree") as mock_rmtree:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["git"], timeout=300)

        with pytest.raises(RuntimeError) as exc:
            github_client.clone_repository("https://github.com/org/repo.git", "/tmp/fake-dir")

        assert str(exc.value) == "Git clone timed out"
        mock_rmtree.assert_called_once_with("/tmp/fake-dir", ignore_errors=True)
