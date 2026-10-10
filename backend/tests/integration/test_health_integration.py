"""Integration tests for live application routing and error middleware."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_not_found_returns_rfc7807_problem_details(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/api/v1/nonexistent-route-xyz")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["status"] == 404
    assert body["code"] == "HTTP_ERROR"
    assert "timestamp" in body
    assert body["instance"] == "/api/v1/nonexistent-route-xyz"


@pytest.mark.integration
async def test_health_and_ready_live_flow(async_client: AsyncClient) -> None:
    health_resp = await async_client.get("/api/v1/healthz")
    assert health_resp.status_code == 200

    ready_resp = await async_client.get("/api/v1/readyz")
    assert ready_resp.status_code == 200
