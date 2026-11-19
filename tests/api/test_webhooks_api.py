import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.src.main import app


@pytest.mark.asyncio
async def test_webhook_ping_event():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/webhooks/github",
            headers={"X-GitHub-Event": "ping"},
            json={"zen": "Non-blocking is better than blocking."},
        )
        assert res.status_code == 202
        data = res.json()
        assert data["status"] == "pong"
        assert "Non-blocking" in data["zen"]


@pytest.mark.asyncio
async def test_webhook_push_event_unregistered_repo():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/webhooks/github",
            headers={"X-GitHub-Event": "push"},
            json={
                "repository": {"full_name": "unknown-org/unknown-repo"},
                "ref": "refs/heads/main",
                "before": "0000000000000000000000000000000000000000",
                "after": "1111111111111111111111111111111111111111",
                "commits": [],
            },
        )
        assert res.status_code == 202
        data = res.json()
        assert data["status"] == "ignored"
        assert "not registered" in data["reason"]


@pytest.mark.asyncio
async def test_webhook_pull_request_event():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/webhooks/github",
            headers={"X-GitHub-Event": "pull_request"},
            json={
                "action": "opened",
                "pull_request": {
                    "number": 42,
                    "base": {"ref": "main"},
                    "head": {"ref": "feature/payments", "sha": "abcdef1234567890"},
                },
                "repository": {"full_name": "acme/billing-service"},
            },
        )
        assert res.status_code == 202
        data = res.json()
        assert data["status"] == "acknowledged"
        assert data["pr_number"] == 42
        assert data["head_ref"] == "feature/payments"
