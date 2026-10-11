"""Security and regression tests for role authorization, admin audit, and curriculum idempotency."""

from collections import defaultdict, deque
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.curriculum import LearningObjective, Topic
from app.models.identity import Course, User, UserRole
from app.models.question import Question, QuestionVersion
from app.seeds.seed_all_comprehensive_curriculum import seed_comprehensive_curriculum
from tests.auth_utils import create_authenticated_user


@pytest.mark.integration
async def test_demo_login_environment_gating(
    async_client: AsyncClient,
) -> None:
    """Verify demo login is strictly disabled in production, staging, or when DEBUG is False."""
    original_env = settings.ENVIRONMENT
    original_debug = settings.DEBUG

    try:
        # 1. Production environment lockout
        settings.ENVIRONMENT = "production"
        resp_prod = await async_client.post(
            "/api/v1/auth/demo-login",
            json={"role": "admin", "course_code": "CS340"},
        )
        assert resp_prod.status_code == 403
        assert resp_prod.json()["code"] == "DEMO_LOGIN_DISABLED"

        # 2. Staging environment lockout
        settings.ENVIRONMENT = "staging"
        resp_staging = await async_client.post(
            "/api/v1/auth/demo-login",
            json={"role": "admin", "course_code": "CS340"},
        )
        assert resp_staging.status_code == 403
        assert resp_staging.json()["code"] == "DEMO_LOGIN_DISABLED"

        # 3. Development environment with DEBUG=False lockout
        settings.ENVIRONMENT = "development"
        settings.DEBUG = False
        resp_nodebug = await async_client.post(
            "/api/v1/auth/demo-login",
            json={"role": "admin", "course_code": "CS340"},
        )
        assert resp_nodebug.status_code == 403
        assert resp_nodebug.json()["code"] == "DEMO_LOGIN_DISABLED"

        # 4. Allowed development environment with DEBUG=True succeeds
        settings.ENVIRONMENT = "development"
        settings.DEBUG = True
        resp_dev = await async_client.post(
            "/api/v1/auth/demo-login",
            json={"role": "student", "course_code": "CS340"},
        )
        assert resp_dev.status_code == 200
        assert resp_dev.json()["user"]["role"] == "student"

    finally:
        settings.ENVIRONMENT = original_env
        settings.DEBUG = original_debug


@pytest.mark.integration
async def test_demo_login_forged_roles_rejected(
    async_client: AsyncClient,
) -> None:
    """Verify invalid or forged role strings are rejected with 422 schema validation error."""
    forged_roles = ["superuser", "root", "hacker", "dean", "auditor_vip"]
    for role in forged_roles:
        resp = await async_client.post(
            "/api/v1/auth/demo-login",
            json={"role": role, "course_code": "CS340"},
        )
        assert resp.status_code == 422
        assert "invalid_params" in resp.json() or resp.json().get("code") == "VALIDATION_ERROR"


@pytest.mark.integration
async def test_admin_endpoint_authorization(
    async_client: AsyncClient,
) -> None:
    """Verify admin audit endpoints strictly reject students and instructors with HTTP 403."""
    # 1. Create a student
    _, student_headers = await create_authenticated_user(
        async_client,
        email="test_student_audit@recall.edu",
        role="student",
    )

    # 2. Create an instructor
    _, inst_headers = await create_authenticated_user(
        async_client,
        email="test_inst_audit@recall.edu",
        role="instructor",
    )

    # 3. Create an administrator
    _, admin_headers = await create_authenticated_user(
        async_client,
        email="test_admin_audit@recall.edu",
        role="admin",
    )

    admin_endpoints = [
        "/api/v1/admin/audit-summary",
        "/api/v1/admin/audit-logs",
    ]

    for endpoint in admin_endpoints:
        # Unauthenticated: 401
        res_unauth = await async_client.get(endpoint)
        assert res_unauth.status_code == 401, f"Expected 401 for unauthenticated on {endpoint}"

        # Student: 403
        res_student = await async_client.get(endpoint, headers=student_headers)
        assert res_student.status_code == 403, f"Expected 403 for student on {endpoint}"
        assert res_student.json()["code"] == "FORBIDDEN"

        # Instructor: 403
        res_inst = await async_client.get(endpoint, headers=inst_headers)
        assert res_inst.status_code == 403, f"Expected 403 for instructor on {endpoint}"
        assert res_inst.json()["code"] == "FORBIDDEN"

        # Admin: 200
        res_admin = await async_client.get(endpoint, headers=admin_headers)
        assert res_admin.status_code == 200, f"Expected 200 for admin on {endpoint}"

    # Verify audit-summary payload structure
    summary_resp = await async_client.get(
        "/api/v1/admin/audit-summary",
        headers=admin_headers,
    )
    data = summary_resp.json()
    assert "system_telemetry" in data
    assert "aggregate_counts" in data
    assert "course_summaries" in data
    assert data["system_telemetry"]["adr_0001_deterministic_grader"] == "ENFORCED"
    assert data["system_telemetry"]["adr_0002_assessment_lockout"] == "ACTIVE"


@pytest.mark.integration
async def test_curriculum_seeder_idempotency_and_dag_validity(
    test_db_session: AsyncSession,
) -> None:
    """Verify seeder idempotency (run twice = 0 duplicates) and DAG cycle-freedom."""
    # Run 1
    res1 = await seed_comprehensive_curriculum(test_db_session)
    assert res1["status"] == "success"

    # Query counts after Run 1
    topics_1 = (await test_db_session.execute(select(Topic))).scalars().all()
    objectives_1 = (await test_db_session.execute(select(LearningObjective))).scalars().all()
    questions_1 = (await test_db_session.execute(select(Question))).scalars().all()
    versions_1 = (await test_db_session.execute(select(QuestionVersion))).scalars().all()

    # Run 2
    res2 = await seed_comprehensive_curriculum(test_db_session)
    assert res2["status"] == "success"
    assert res2["dbms_new_questions"] == 0
    assert res2["os_new_questions"] == 0

    # Query counts after Run 2
    topics_2 = (await test_db_session.execute(select(Topic))).scalars().all()
    objectives_2 = (await test_db_session.execute(select(LearningObjective))).scalars().all()
    questions_2 = (await test_db_session.execute(select(Question))).scalars().all()
    versions_2 = (await test_db_session.execute(select(QuestionVersion))).scalars().all()

    # Zero duplicate assertion
    assert len(topics_1) == len(topics_2), "Topics count changed on second seed!"
    assert len(objectives_1) == len(objectives_2), "Objectives count changed on second seed!"
    assert len(questions_1) == len(questions_2), "Questions count changed on second seed!"
    assert len(versions_1) == len(versions_2), "Question versions count changed on second seed!"

    # DAG Integrity & Acyclicity Verification
    all_obj_ids = {obj.id for obj in objectives_2}
    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {obj.id: 0 for obj in objectives_2}

    for obj in objectives_2:
        for prereq_id in obj.prerequisite_objective_ids:
            # Prerequisite node must exist
            assert prereq_id in all_obj_ids, (
                f"Objective '{obj.code}' references non-existent prerequisite ID '{prereq_id}'"
            )
            adj[prereq_id].append(obj.id)
            in_degree[obj.id] += 1

    # Topological sort (Kahn's algorithm) to prove acyclicity
    queue = deque([oid for oid, deg in in_degree.items() if deg == 0])
    visited_count = 0

    while queue:
        curr = queue.popleft()
        visited_count += 1
        for nxt in adj[curr]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)

    assert visited_count == len(all_obj_ids), "Cycle detected in curriculum DAG!"

    # Verify every question has valid answer_key, rubric, and provenance_hash
    for v in versions_2:
        assert v.prompt and len(v.prompt.strip()) > 0
        assert v.answer_key is not None
        assert v.rubric is not None
        assert v.provenance_hash and len(v.provenance_hash) == 64  # SHA-256
