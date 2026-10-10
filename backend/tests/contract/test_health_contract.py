"""Contract tests validating OpenAPI schema and health response contracts."""

import pytest
from httpx import AsyncClient


@pytest.mark.contract
async def test_openapi_schema_contains_health_and_problem_details(
    async_client: AsyncClient,
) -> None:
    response = await async_client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    assert "/api/v1/healthz" in schema["paths"]
    assert "/api/v1/readyz" in schema["paths"]
    assert "ProblemDetails" in schema["components"]["schemas"]


@pytest.mark.contract
async def test_healthz_contract_format(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/healthz")
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"status", "environment", "version"}
    assert data["status"] == "ok"


@pytest.mark.contract
async def test_readyz_contract_format(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/readyz")
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"status", "engines"}
    assert data["status"] == "ready"
    assert "adaptive_learning_engine" in data["engines"]
    assert "knowledge_engine" in data["engines"]
    assert "ai_execution_engine" in data["engines"]
