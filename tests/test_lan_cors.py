"""
tests/test_lan_cors.py

Tests for LAN CORS configuration and network accessibility.
Verifies:
1. CORS headers are permitted for RFC 1918 LAN origins (10.x.x.x, 192.168.x.x, 172.16-31.x.x).
2. CORS headers are permitted for localhost and 127.0.0.1 origins.
3. Untrusted public external origins do not receive permissive CORS headers.
4. /health endpoint is accessible with LAN origins.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.src.main import app


@pytest.mark.asyncio
async def test_cors_allows_private_lan_10_origin():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/health",
            headers={"Origin": "http://10.0.0.59:3000"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://10.0.0.59:3000"
        assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_allows_private_lan_192_origin():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/health",
            headers={"Origin": "http://192.168.1.42:8080"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://192.168.1.42:8080"


@pytest.mark.asyncio
async def test_cors_allows_private_lan_172_origin():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/health",
            headers={"Origin": "http://172.20.0.10:3000"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://172.20.0.10:3000"


@pytest.mark.asyncio
async def test_cors_allows_localhost_origin():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.asyncio
async def test_cors_rejects_untrusted_public_origin():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/health",
            headers={"Origin": "http://malicious-public-site.com"},
        )
        assert response.status_code == 200
        # Untrusted public origin should NOT receive access-control-allow-origin
        assert response.headers.get("access-control-allow-origin") is None
