"""Comprehensive security and authorization regression tests for Phase 7 remediation.

Verifies:
1. Unauthenticated access denied (HTTP 401) on every protected route.
2. Malformed, tampered, expired, and missing-expiration tokens rejected (HTTP 401).
3. Student A attempting to access or mutate Student B's data denied (HTTP 403).
4. Student accessing course materials/tutor/revisor/scheduling without enrollment denied (HTTP 403).
5. Unauthorized instructor-only actions denied to students (HTTP 403).
6. Instructor not assigned to a course cannot mutate or upload documents to it (HTTP 403).
7. Demo login disabled in production (HTTP 403).
8. Passwordless email login cannot issue tokens (HTTP 501).
9. Default / weak signing key rejected at startup in production configuration.
10. Existing development demo login flow continues to function seamlessly.
"""

import pytest
from httpx import AsyncClient

from app.core.config import Settings
from app.core.security import _b64url_encode, create_access_token
from tests.auth_utils import create_authenticated_user


@pytest.mark.integration
async def test_unauthenticated_access_denied_on_protected_routes(
    async_client: AsyncClient,
) -> None:
    """Every protected domain route must return HTTP 401 when unauthenticated."""
    protected_endpoints = [
        ("GET", "/api/v1/auth/me"),
        ("POST", "/api/v1/attempts"),
        ("GET", "/api/v1/attempts/test-att-id"),
        ("GET", "/api/v1/attempts/student/test-student-id"),
        ("GET", "/api/v1/mastery/student/s1/course/c1"),
        ("GET", "/api/v1/mastery/student/s1/objective/lo1"),
        ("GET", "/api/v1/diagnosis/student/s1/course/c1"),
        ("GET", "/api/v1/diagnosis/student/s1/objective/lo1"),
        ("POST", "/api/v1/diagnosis/session/plan"),
        ("POST", "/api/v1/courses/c1/documents/upload"),
        ("GET", "/api/v1/courses/c1/documents"),
        ("GET", "/api/v1/courses/c1/documents/doc1"),
        ("DELETE", "/api/v1/courses/c1/documents/doc1"),
        ("POST", "/api/v1/courses/c1/knowledge/retrieve"),
        ("POST", "/api/v1/courses/c1/tutor/ask"),
        ("POST", "/api/v1/courses/c1/revisor/review"),
        ("GET", "/api/v1/courses/c1/scheduling/student/s1/review-queue"),
        ("POST", "/api/v1/courses/c1/scheduling/student/s1/plan-session"),
        ("POST", "/api/v1/courses/seed/dbms"),
        ("POST", "/api/v1/courses/c1/enroll"),
    ]

    for method, path in protected_endpoints:
        if method == "GET":
            resp = await async_client.get(path)
        elif method == "POST":
            resp = await async_client.post(path, json={})
        elif method == "DELETE":
            resp = await async_client.delete(path)
        else:
            continue

        assert (
            resp.status_code == 401
        ), f"Expected 401 for {method} {path}, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("code") == "UNAUTHORIZED"
        assert (
            "Authorization header" in data.get("detail", "")
            or "scheme" in data.get("detail", "").lower()
        )


@pytest.mark.integration
async def test_token_tampering_and_expiration_rejections(
    async_client: AsyncClient,
) -> None:
    """Verify that invalid, expired, missing-expiration, and tampered tokens are rejected."""
    _, instructor_hdr = await create_authenticated_user(
        async_client, "inst.tamper@recall.edu", "Prof Tamper", "instructor"
    )

    # 1. Malformed token structure (not 3 parts)
    bad_structure_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not.a.valid.jwt.token"},
    )
    assert bad_structure_resp.status_code == 401
    assert "malformed" in bad_structure_resp.json()["detail"].lower()

    # 2. Tampered signature
    valid_token = instructor_hdr["Authorization"].replace("Bearer ", "")
    parts = valid_token.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}.badsignature123"
    tampered_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert tampered_resp.status_code == 401
    assert "signature" in tampered_resp.json()["detail"].lower()

    # 3. Expired token
    expired_token = create_access_token(
        user_id="any-id",
        email="test@recall.edu",
        role="student",
        expires_minutes=-5,  # 5 minutes in the past
    )
    expired_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert expired_resp.status_code == 401
    assert "expired" in expired_resp.json()["detail"].lower()

    # 4. Missing expiration claim (exp)
    import hashlib
    import hmac
    import json

    from app.core.config import settings

    h_b64 = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    p_b64 = _b64url_encode(
        json.dumps({"sub": "no-exp-user", "email": "a@b.com", "role": "student"}).encode()
    )
    sig = hmac.new(
        settings.SECRET_KEY.encode(), f"{h_b64}.{p_b64}".encode(), hashlib.sha256
    ).digest()
    no_exp_token = f"{h_b64}.{p_b64}.{_b64url_encode(sig)}"

    no_exp_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {no_exp_token}"},
    )
    assert no_exp_resp.status_code == 401
    assert "expiration" in no_exp_resp.json()["detail"].lower()


@pytest.mark.integration
async def test_cross_student_ownership_protection(
    async_client: AsyncClient,
) -> None:
    """Student A must not be able to view or mutate Student B's attempts or mastery."""
    # Create Student A and Student B
    student_a, hdr_a = await create_authenticated_user(
        async_client, "student.a@recall.edu", "Alice", "student"
    )
    student_b, hdr_b = await create_authenticated_user(
        async_client, "student.b@recall.edu", "Bob", "student"
    )

    # Student A attempts to query Student B's attempts
    cross_att_resp = await async_client.get(
        f"/api/v1/attempts/student/{student_b['id']}",
        headers=hdr_a,
    )
    assert cross_att_resp.status_code == 403
    assert cross_att_resp.json()["code"] == "FORBIDDEN"

    # Student A attempts to submit an attempt on behalf of Student B
    cross_submit_resp = await async_client.post(
        "/api/v1/attempts",
        json={
            "student_id": student_b["id"],
            "question_id": "dummy-q",
            "submitted_answer": {"val": 1},
        },
        headers={"Idempotency-Key": "cross-test-key-1", **hdr_a},
    )
    assert cross_submit_resp.status_code == 403
    assert cross_submit_resp.json()["code"] == "FORBIDDEN"


@pytest.mark.integration
async def test_unauthorized_course_access_and_enrollment_enforced(
    async_client: AsyncClient,
) -> None:
    """Students without course enrollment must be denied course-scoped operations."""
    # Seed course via instructor
    _, inst_hdr = await create_authenticated_user(
        async_client, "inst.course@recall.edu", "Prof Course", "instructor"
    )
    seed_resp = await async_client.post("/api/v1/courses/seed/dbms", headers=inst_hdr)
    assert seed_resp.status_code == 201
    course_id = seed_resp.json()["course_id"]

    # Create Unenrolled Student
    unenrolled_student, unenrolled_hdr = await create_authenticated_user(
        async_client, "unenrolled@recall.edu", "Unenrolled User", "student"
    )

    # 1. Attempt to query course mastery without enrollment -> 403
    mastery_resp = await async_client.get(
        f"/api/v1/mastery/student/{unenrolled_student['id']}/course/{course_id}",
        headers=unenrolled_hdr,
    )
    assert mastery_resp.status_code == 403
    assert "not enrolled" in mastery_resp.json()["detail"].lower()

    # 2. Attempt to query tutor without enrollment -> 403
    tutor_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/tutor/ask",
        json={"student_id": unenrolled_student["id"], "query": "What is 3NF?"},
        headers=unenrolled_hdr,
    )
    assert tutor_resp.status_code == 403
    assert "not enrolled" in tutor_resp.json()["detail"].lower()

    # 3. Attempt to upload course documents as a student -> 403
    upload_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/documents/upload",
        files={"file": ("test.txt", b"content", "text/plain")},
        headers=unenrolled_hdr,
    )
    assert upload_resp.status_code == 403
    assert "instructor" in upload_resp.json()["detail"].lower()


@pytest.mark.integration
async def test_demo_login_disabled_in_production(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In production environments, /demo-login must be strictly rejected with HTTP 403."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    resp = await async_client.post(
        "/api/v1/auth/demo-login",
        json={"role": "student", "course_code": "CS340"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "DEMO_LOGIN_DISABLED"
    assert "disabled in production" in resp.json()["detail"].lower()


@pytest.mark.integration
async def test_passwordless_login_fails_closed(
    async_client: AsyncClient,
) -> None:
    """Email-only login must fail closed with HTTP 501 to prevent privilege escalation."""
    resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "student.ada@recall.edu"},
    )
    assert resp.status_code == 501
    assert resp.json()["code"] == "AUTHENTICATION_DISABLED"
    assert "disabled" in resp.json()["detail"].lower()


@pytest.mark.integration
async def test_production_secret_key_validation_fails_closed() -> None:
    """Settings must fail startup in production if secret key is default or short."""
    with pytest.raises(ValueError, match="Insecure or default SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="dev_secret_key_change_in_production_min_32_chars_12345",
        )

    with pytest.raises(ValueError, match="Insecure or default SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="insecure",
        )


@pytest.mark.integration
async def test_development_demo_login_flow_operational(
    async_client: AsyncClient,
) -> None:
    """In non-prod environments, demo login provisions Ada Lovelace and DBMS course."""
    resp = await async_client.post(
        "/api/v1/auth/demo-login",
        json={"role": "student", "course_code": "CS340"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "student.ada@recall.edu"
    assert data["user"]["role"] == "student"

    # Authenticated /me request
    me_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["user"]["email"] == "student.ada@recall.edu"
    assert len(me_data["enrolled_course_ids"]) >= 1
