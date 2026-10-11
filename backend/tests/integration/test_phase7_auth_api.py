"""Integration tests for Phase 7: Authentication API, Token Verification,
and Server-Side Authorization.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
async def test_auth_api_lifecycle_and_security(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    # 1. Unauthenticated /me should return 401 Problem Details
    unauth_resp = await async_client.get("/api/v1/auth/me")
    assert unauth_resp.status_code == 401
    problem = unauth_resp.json()
    assert problem["code"] == "UNAUTHORIZED"
    assert "Authorization header" in problem["detail"]

    # 2. Invalid Bearer Token should return 401
    bad_token_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert bad_token_resp.status_code == 401
    assert bad_token_resp.json()["code"] == "UNAUTHORIZED"

    # 3. Demo login for Student (Ada Lovelace)
    demo_student_resp = await async_client.post(
        "/api/v1/auth/demo-login",
        json={"role": "student", "course_code": "CS340"},
    )
    assert demo_student_resp.status_code == 200
    student_data = demo_student_resp.json()
    assert "access_token" in student_data
    assert student_data["token_type"] == "bearer"
    assert student_data["user"]["email"] == "student.ada@recall.edu"
    assert student_data["user"]["role"] == "student"
    student_token = student_data["access_token"]
    student_id = student_data["user"]["id"]

    # 4. Authenticated /me request with Bearer token
    me_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["user"]["id"] == student_id
    assert len(me_data["enrolled_course_ids"]) >= 1

    # 5. Regular email login for the existing student
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "student.ada@recall.edu"},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["id"] == student_id

    # 6. Demo login for Instructor (Prof. E. F. Codd)
    demo_inst_resp = await async_client.post(
        "/api/v1/auth/demo-login",
        json={"role": "instructor", "course_code": "CS340"},
    )
    assert demo_inst_resp.status_code == 200
    inst_data = demo_inst_resp.json()
    assert inst_data["user"]["email"] == "instructor.dbms@recall.edu"
    assert inst_data["user"]["role"] == "instructor"

    # 7. Non-existent email login should return 404
    non_existent_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@recall.edu"},
    )
    assert non_existent_resp.status_code == 404
    assert non_existent_resp.json()["code"] == "RESOURCE_NOT_FOUND"
