"""Authentication and test token helpers for integration tests."""

from httpx import AsyncClient

from app.core.security import create_access_token


def make_auth_headers(
    user_id: str,
    email: str = "test@recall.edu",
    role: str = "student",
) -> dict[str, str]:
    """Generate valid Authorization header with signed Bearer token."""
    token = create_access_token(user_id=user_id, email=email, role=role)
    return {"Authorization": f"Bearer {token}"}


async def create_authenticated_user(
    client: AsyncClient,
    email: str = "test.user@recall.edu",
    full_name: str = "Test User",
    role: str = "student",
) -> tuple[dict, dict[str, str]]:
    """Register a user via API and return user dict and auth headers."""
    resp = await client.post(
        "/api/v1/users",
        json={"email": email, "full_name": full_name, "role": role},
    )
    assert resp.status_code == 201
    user_data = resp.json()
    headers = make_auth_headers(user_id=user_data["id"], email=email, role=role)
    return user_data, headers
