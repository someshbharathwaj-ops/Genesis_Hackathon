"""Integration and contract tests for Phase 1 identity,
courses, versioned questions, and idempotent attempts.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.question import QuestionVersion


def _auth(user_id: str, email: str = "test@recall.edu", role: str = "student") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(user_id=user_id, email=email, role=role)}"
    }


@pytest.mark.integration
async def test_full_phase1_lifecycle_and_idempotency(async_client: AsyncClient) -> None:
    # 1. Create Student User
    user_resp = await async_client.post(
        "/api/v1/users",
        json={"email": "student1@recall.edu", "full_name": "Alice Turing", "role": "student"},
    )
    assert user_resp.status_code == 201
    student = user_resp.json()
    student_id = student["id"]

    # 2. Create Course
    course_resp = await async_client.post(
        "/api/v1/courses",
        json={
            "code": "CS340",
            "title": "Database Management Systems",
            "description": "Relational Theory and Normalization",
        },
    )
    assert course_resp.status_code == 201
    course = course_resp.json()
    course_id = course["id"]

    # 3. Create Topic
    topic_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/topics",
        json={
            "code": "FD_NORM",
            "title": "Functional Dependencies & Normalization",
            "order_index": 1,
        },
    )
    assert topic_resp.status_code == 201
    topic = topic_resp.json()
    topic_id = topic["id"]

    # 4. Create Learning Objective
    lo_resp = await async_client.post(
        f"/api/v1/courses/topics/{topic_id}/objectives",
        json={
            "code": "LO_CLOSURE",
            "title": "Compute Attribute Closure",
            "description": "Calculate X+ given relation R and set of FDs F",
            "prerequisite_objective_ids": [],
        },
    )
    assert lo_resp.status_code == 201
    lo = lo_resp.json()
    lo_id = lo["id"]

    # 5. Create Question with Verified Initial Version
    q_resp = await async_client.post(
        "/api/v1/questions",
        json={
            "objective_id": lo_id,
            "title": "Closure of Attribute A",
            "question_type": "multiple_choice",
            "initial_version": {
                "prompt": "Given R(A, B, C) and F={A->B, B->C}, what is {A}+?",
                "difficulty": "introductory",
                "max_score": 1.0,
                "options": [
                    {"id": "opt1", "text": "A"},
                    {"id": "opt2", "text": "A, B"},
                    {"id": "opt3", "text": "A, B, C"},
                ],
                "answer_key": {"value": "A, B, C", "reference": "Armstrong Transitivity"},
                "rubric": {"criterion": "Complete closure", "points": 1.0},
                "verification_status": "verified",
                "verified_by": "Prof. Codd",
            },
        },
    )
    assert q_resp.status_code == 201
    question = q_resp.json()
    question_id = question["id"]
    assert len(question["versions"]) == 1
    v1 = question["versions"][0]
    assert v1["version_number"] == 1
    assert v1["verification_status"] == "verified"
    assert len(v1["provenance_hash"]) == 64

    # 6. Add Version 2 to Question
    v2_resp = await async_client.post(
        f"/api/v1/questions/{question_id}/versions",
        json={
            "prompt": "Given R(A, B, C, D) and F={A->B, B->C, C->D}, what is {A}+?",
            "difficulty": "intermediate",
            "max_score": 2.0,
            "answer_key": {"value": "A, B, C, D"},
            "rubric": {"criterion": "Four attribute closure", "points": 2.0},
            "verification_status": "verified",
            "verified_by": "Prof. Date",
        },
    )
    assert v2_resp.status_code == 201
    v2 = v2_resp.json()
    assert v2["version_number"] == 2
    assert v2["provenance_hash"] != v1["provenance_hash"]

    # 7. Submit First Scored Attempt with Idempotency-Key
    idem_key = "test-idem-key-001"
    attempt_payload = {
        "student_id": student_id,
        "question_id": question_id,
        "submitted_answer": {"value": "A, B, C, D"},
        "is_hint_assisted": False,
        "hint_count": 0,
        "time_spent_ms": 12000,
        "assessment_context": "diagnostic",
    }
    att_resp = await async_client.post(
        "/api/v1/attempts",
        json=attempt_payload,
        headers={"Idempotency-Key": idem_key, **_auth(student_id, student["email"])},
    )
    assert att_resp.status_code == 201
    attempt = att_resp.json()
    assert attempt["is_correct"] is True
    assert attempt["score_achieved"] == 2.0
    assert attempt["grading_provenance"]["version_number"] == 2
    assert attempt["grading_provenance"]["repetition_discount_applied"] is False

    # 8. Replay identical attempt submission with same Idempotency-Key -> 200 OK
    replay_resp = await async_client.post(
        "/api/v1/attempts",
        json=attempt_payload,
        headers={"Idempotency-Key": idem_key, **_auth(student_id, student["email"])},
    )
    assert replay_resp.status_code == 200
    replayed = replay_resp.json()
    assert replayed["id"] == attempt["id"]
    assert replayed["score_achieved"] == 2.0

    # 9. Negative Test: Reuse same Idempotency-Key with conflicting answer -> 409 Conflict
    conflict_payload = {
        "student_id": student_id,
        "question_id": question_id,
        "submitted_answer": {"value": "DIFFERENT_ANSWER"},
        "is_hint_assisted": False,
        "hint_count": 0,
        "time_spent_ms": 5000,
        "assessment_context": "diagnostic",
    }
    conflict_resp = await async_client.post(
        "/api/v1/attempts",
        json=conflict_payload,
        headers={"Idempotency-Key": idem_key, **_auth(student_id, student["email"])},
    )
    assert conflict_resp.status_code == 409
    assert conflict_resp.headers["content-type"] == "application/problem+json"
    conflict_data = conflict_resp.json()
    assert conflict_data["code"] == "IDEMPOTENCY_CONFLICT"


@pytest.mark.integration
async def test_attempt_with_hint_penalty_and_repetition_discount(
    async_client: AsyncClient,
) -> None:
    # Create student and question
    u_resp = await async_client.post(
        "/api/v1/users",
        json={"email": "student2@recall.edu", "full_name": "Bob Bodd", "role": "student"},
    )
    student_id = u_resp.json()["id"]

    c_resp = await async_client.post(
        "/api/v1/courses",
        json={"code": "CS341", "title": "DB Systems 2"},
    )
    course_id = c_resp.json()["id"]

    t_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/topics",
        json={"code": "T1", "title": "Topic 1"},
    )
    topic_id = t_resp.json()["id"]

    lo_resp = await async_client.post(
        f"/api/v1/courses/topics/{topic_id}/objectives",
        json={"code": "LO1", "title": "LO 1", "description": "LO 1 Desc"},
    )
    lo_id = lo_resp.json()["id"]

    q_resp = await async_client.post(
        "/api/v1/questions",
        json={
            "objective_id": lo_id,
            "title": "Question with Hints",
            "initial_version": {
                "prompt": "What is 2+2?",
                "max_score": 10.0,
                "answer_key": {"value": "4"},
                "rubric": {"criterion": "Correct value", "points": 10.0},
                "verification_status": "verified",
            },
        },
    )
    question_id = q_resp.json()["id"]

    # Submit with 2 hints used (hint penalty should reduce score)
    att_resp = await async_client.post(
        "/api/v1/attempts",
        json={
            "student_id": student_id,
            "question_id": question_id,
            "submitted_answer": {"value": "4"},
            "is_hint_assisted": True,
            "hint_count": 2,
            "time_spent_ms": 30000,
        },
        headers={"Idempotency-Key": "hint-att-001", **_auth(student_id, "student2@recall.edu")},
    )
    assert att_resp.status_code == 201
    att = att_resp.json()
    assert att["is_correct"] is True
    # 2 hints * 0.25 = 0.50 penalty -> 10.0 * 0.5 = 5.0
    assert att["score_achieved"] == 5.0
    assert att["is_hint_assisted"] is True
    assert att["hint_count"] == 2

    # Second attempt on same question: repetition discount flagged
    att_resp2 = await async_client.post(
        "/api/v1/attempts",
        json={
            "student_id": student_id,
            "question_id": question_id,
            "submitted_answer": {"value": "4"},
            "is_hint_assisted": False,
            "hint_count": 0,
            "time_spent_ms": 15000,
        },
        headers={"Idempotency-Key": "repeat-att-002", **_auth(student_id, "student2@recall.edu")},
    )
    assert att_resp2.status_code == 201
    att2 = att_resp2.json()
    assert att2["grading_provenance"]["repetition_discount_applied"] is True
    assert att2["grading_provenance"]["prior_attempt_count"] == 1


@pytest.mark.integration
async def test_attempt_fails_when_no_verified_version_exists(
    async_client: AsyncClient,
) -> None:
    u_resp = await async_client.post(
        "/api/v1/users",
        json={"email": "student3@recall.edu", "full_name": "Charlie", "role": "student"},
    )
    student_id = u_resp.json()["id"]

    c_resp = await async_client.post(
        "/api/v1/courses",
        json={"code": "CS342", "title": "DB Systems 3"},
    )
    course_id = c_resp.json()["id"]

    t_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/topics",
        json={"code": "T2", "title": "Topic 2"},
    )
    topic_id = t_resp.json()["id"]

    lo_resp = await async_client.post(
        f"/api/v1/courses/topics/{topic_id}/objectives",
        json={"code": "LO2", "title": "LO 2", "description": "LO 2 Desc"},
    )
    lo_id = lo_resp.json()["id"]

    # Create unverified question (draft status)
    q_resp = await async_client.post(
        "/api/v1/questions",
        json={
            "objective_id": lo_id,
            "title": "Unverified Question",
            "initial_version": {
                "prompt": "Unverified draft prompt?",
                "answer_key": {"value": "draft"},
                "rubric": {"criterion": "draft", "points": 1.0},
                "verification_status": "draft",
            },
        },
    )
    question_id = q_resp.json()["id"]

    # Submitting for scored diagnostic context must fail with 422 UNVERIFIED_EVIDENCE
    att_resp = await async_client.post(
        "/api/v1/attempts",
        json={
            "student_id": student_id,
            "question_id": question_id,
            "submitted_answer": {"value": "draft"},
            "assessment_context": "diagnostic",
        },
        headers={
            "Idempotency-Key": "unverified-att-001",
            **_auth(student_id, "student3@recall.edu"),
        },
    )
    assert att_resp.status_code == 422
    err_body = att_resp.json()
    assert err_body["code"] == "UNVERIFIED_EVIDENCE"


@pytest.mark.integration
async def test_identity_and_course_conflict_and_queries(
    async_client: AsyncClient,
) -> None:
    # 1. Duplicate user conflict
    await async_client.post(
        "/api/v1/users",
        json={"email": "unique@recall.edu", "full_name": "Unique User", "role": "student"},
    )
    dup_user_resp = await async_client.post(
        "/api/v1/users",
        json={"email": "unique@recall.edu", "full_name": "Duplicate User", "role": "student"},
    )
    assert dup_user_resp.status_code == 409
    assert dup_user_resp.json()["code"] == "USER_EMAIL_EXISTS"

    # 2. Duplicate course code conflict
    await async_client.post(
        "/api/v1/courses",
        json={"code": "UNIQUE_CS", "title": "Unique CS Course"},
    )
    dup_course_resp = await async_client.post(
        "/api/v1/courses",
        json={"code": "UNIQUE_CS", "title": "Duplicate CS Course"},
    )
    assert dup_course_resp.status_code == 409
    assert dup_course_resp.json()["code"] == "COURSE_CODE_EXISTS"

    # 3. User listing and retrieval
    users_resp = await async_client.get("/api/v1/users")
    assert users_resp.status_code == 200
    assert len(users_resp.json()) >= 1
    first_user_id = users_resp.json()[0]["id"]

    get_user_resp = await async_client.get(f"/api/v1/users/{first_user_id}")
    assert get_user_resp.status_code == 200
    assert get_user_resp.json()["id"] == first_user_id

    # 4. Course listing and retrieval
    courses_resp = await async_client.get("/api/v1/courses")
    assert courses_resp.status_code == 200
    assert len(courses_resp.json()) >= 1
    first_course_id = courses_resp.json()[0]["id"]

    get_course_resp = await async_client.get(f"/api/v1/courses/{first_course_id}")
    assert get_course_resp.status_code == 200

    # 5. Course enrollment
    enroll_resp = await async_client.post(
        f"/api/v1/courses/{first_course_id}/enroll",
        json={"user_id": first_user_id, "course_id": first_course_id},
        headers=_auth(first_user_id),
    )
    assert enroll_resp.status_code == 201

    # Re-enroll returns existing 201/200
    re_enroll = await async_client.post(
        f"/api/v1/courses/{first_course_id}/enroll",
        json={"user_id": first_user_id, "course_id": first_course_id},
        headers=_auth(first_user_id),
    )
    assert re_enroll.status_code == 201

    # 6. Not found negative tests
    assert (await async_client.get("/api/v1/users/nonexistent-user")).status_code == 404
    assert (await async_client.get("/api/v1/courses/nonexistent-course")).status_code == 404
    assert (await async_client.get("/api/v1/questions/nonexistent-q")).status_code == 404
    assert (
        await async_client.get("/api/v1/attempts/nonexistent-att", headers=_auth(first_user_id))
    ).status_code == 404


@pytest.mark.integration
async def test_seed_dbms_curriculum_and_idempotency(async_client: AsyncClient) -> None:
    # 0. Setup admin user for seeding
    adm_resp = await async_client.post(
        "/api/v1/users",
        json={"email": "seed_admin@recall.edu", "full_name": "Seed Admin", "role": "admin"},
    )
    adm_id = adm_resp.json()["id"]
    adm_hdr = _auth(adm_id, "seed_admin@recall.edu", role="admin")

    # 1. First seeding creates the course, topic, 5 objectives, and catalog questions
    seed_resp = await async_client.post("/api/v1/courses/seed/dbms", headers=adm_hdr)
    assert seed_resp.status_code == 201
    data = seed_resp.json()
    assert data["status"] == "success"
    assert data["objectives_count"] == 5
    assert data["new_questions_seeded"] >= 8

    # 2. Second seeding is strictly idempotent (0 new questions created)
    re_seed_resp = await async_client.post("/api/v1/courses/seed/dbms", headers=adm_hdr)
    assert re_seed_resp.status_code == 201
    re_data = re_seed_resp.json()
    assert re_data["status"] == "success"
    assert re_data["new_questions_seeded"] == 0


@pytest.mark.integration
async def test_question_version_with_attempts_cannot_be_deleted(
    async_client: AsyncClient, test_db_session: AsyncSession
) -> None:
    # 1. Setup entities
    u_resp = await async_client.post(
        "/api/v1/users",
        json={"email": "restrict_test@recall.edu", "full_name": "Restrict User", "role": "student"},
    )
    student_id = u_resp.json()["id"]

    c_resp = await async_client.post(
        "/api/v1/courses",
        json={"code": "RESTRICT_CS", "title": "Restrict Test Course"},
    )
    course_id = c_resp.json()["id"]

    t_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/topics",
        json={"code": "RESTRICT_TOPIC", "title": "Topic Restrict"},
    )
    topic_id = t_resp.json()["id"]

    lo_resp = await async_client.post(
        f"/api/v1/courses/topics/{topic_id}/objectives",
        json={"code": "LO_RESTRICT", "title": "Restrict LO", "description": "Test"},
    )
    lo_id = lo_resp.json()["id"]

    q_resp = await async_client.post(
        "/api/v1/questions",
        json={
            "objective_id": lo_id,
            "title": "Restrict Question",
            "question_type": "multiple_choice",
            "initial_version": {
                "prompt": "Prompt?",
                "difficulty": "introductory",
                "max_score": 1.0,
                "answer_key": {"value": "A"},
                "rubric": {"points": 1.0},
                "verification_status": "verified",
            },
        },
    )
    q_data = q_resp.json()
    q_id = q_data["id"]
    version_id = q_data["versions"][0]["id"]

    # 2. Submit an attempt referencing this version
    att_resp = await async_client.post(
        "/api/v1/attempts",
        json={
            "student_id": student_id,
            "question_id": q_id,
            "submitted_answer": {"value": "A"},
            "assessment_context": "diagnostic",
        },
        headers={
            "Idempotency-Key": "restrict-test-att-001",
            **_auth(student_id, "restrict_test@recall.edu"),
        },
    )
    assert att_resp.status_code == 201

    # 3. Database-level guarantee: Attempting to delete the question version
    # directly raises IntegrityError via ondelete="RESTRICT"
    v_obj = await test_db_session.get(QuestionVersion, version_id)
    assert v_obj is not None

    with pytest.raises(IntegrityError):
        await test_db_session.delete(v_obj)
        await test_db_session.commit()

    await test_db_session.rollback()


@pytest.mark.integration
async def test_idempotency_database_unique_constraint_and_replay(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    # 1. Setup student and question
    u_resp = await async_client.post(
        "/api/v1/users",
        json={
            "email": "concurrent_test@recall.edu",
            "full_name": "Concurrent User",
            "role": "student",
        },
    )
    student_id = u_resp.json()["id"]

    c_resp = await async_client.post(
        "/api/v1/courses",
        json={"code": "CONCURRENT_CS", "title": "Concurrent Course"},
    )
    course_id = c_resp.json()["id"]

    t_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/topics",
        json={"code": "CONCURRENT_TOPIC", "title": "Concurrent Topic"},
    )
    topic_id = t_resp.json()["id"]

    lo_resp = await async_client.post(
        f"/api/v1/courses/topics/{topic_id}/objectives",
        json={"code": "LO_CONCURRENT", "title": "Concurrent LO", "description": "Test"},
    )
    lo_id = lo_resp.json()["id"]

    q_resp = await async_client.post(
        "/api/v1/questions",
        json={
            "objective_id": lo_id,
            "title": "Concurrent Question",
            "question_type": "multiple_choice",
            "initial_version": {
                "prompt": "Concurrent Prompt",
                "difficulty": "introductory",
                "max_score": 1.0,
                "answer_key": {"value": "B"},
                "rubric": {"points": 1.0},
                "verification_status": "verified",
            },
        },
    )
    q_data = q_resp.json()
    q_id = q_data["id"]
    version_id = q_data["versions"][0]["id"]

    # 2. First submission via API creates attempt with status 201
    shared_key = "concurrent-idem-key-888"
    payload = {
        "student_id": student_id,
        "question_id": q_id,
        "submitted_answer": {"value": "B"},
        "assessment_context": "diagnostic",
    }

    first_resp = await async_client.post(
        "/api/v1/attempts",
        json=payload,
        headers={"Idempotency-Key": shared_key, **_auth(student_id, "concurrent_test@recall.edu")},
    )
    assert first_resp.status_code == 201
    attempt_id = first_resp.json()["id"]

    # 3. Application-level replay returns existing attempt with status 200
    replay_resp = await async_client.post(
        "/api/v1/attempts",
        json=payload,
        headers={"Idempotency-Key": shared_key, **_auth(student_id, "concurrent_test@recall.edu")},
    )
    assert replay_resp.status_code == 200
    assert replay_resp.json()["id"] == attempt_id

    # 4. Database-level guarantee: Direct attempt to insert a duplicate record
    # with the same idempotency_key fails with an IntegrityError (enforcing unique constraint)
    from app.models.attempt import AssessmentContext, Attempt, AttemptStatus

    duplicate_attempt = Attempt(
        idempotency_key=shared_key,
        student_id=student_id,
        question_id=q_id,
        question_version_id=version_id,
        assessment_context=AssessmentContext.DIAGNOSTIC,
        submitted_answer={"value": "B"},
        status=AttemptStatus.GRADED,
        is_correct=True,
        score_achieved=1.0,
        max_possible_score=1.0,
        grading_provenance={"test": "duplicate_check"},
    )

    with pytest.raises(IntegrityError):
        async with test_db_session.begin_nested():
            test_db_session.add(duplicate_attempt)
            await test_db_session.flush()

    # 5. Verify total student attempts remains exactly 1
    student_atts = await async_client.get(
        f"/api/v1/attempts/student/{student_id}",
        headers=_auth(student_id, "concurrent_test@recall.edu"),
    )
    assert student_atts.status_code == 200
    assert len(student_atts.json()) == 1


@pytest.mark.integration
async def test_cyclic_and_self_prerequisites_rejected(async_client: AsyncClient) -> None:
    # 1. Setup Course & Topic
    c_resp = await async_client.post(
        "/api/v1/courses",
        json={"code": "CYCLE_CS", "title": "Cycle Test Course"},
    )
    course_id = c_resp.json()["id"]

    t_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/topics",
        json={"code": "CYCLE_TOPIC", "title": "Cycle Topic"},
    )
    topic_id = t_resp.json()["id"]

    # 2. Rejection of self-cycle: Objective lists its own code as prerequisite
    self_resp = await async_client.post(
        f"/api/v1/courses/topics/{topic_id}/objectives",
        json={
            "code": "LO_SELF",
            "title": "Self Prerequisite",
            "description": "Invalid",
            "prerequisite_objective_ids": ["LO_SELF"],
        },
    )
    assert self_resp.status_code == 400
    err = self_resp.json()
    assert err["code"] == "CYCLIC_PREREQUISITE"

    # 3. Rejection of unresolved prerequisite: Reference to non-existent objective
    unresolved_resp = await async_client.post(
        f"/api/v1/courses/topics/{topic_id}/objectives",
        json={
            "code": "LO_UNRESOLVED",
            "title": "Unresolved Prereq",
            "description": "Invalid",
            "prerequisite_objective_ids": ["NON_EXISTENT_LO"],
        },
    )
    assert unresolved_resp.status_code == 400
    assert unresolved_resp.json()["code"] == "UNRESOLVED_PREREQUISITE"

    # 4. Create base LO_A requiring nothing
    lo_a_resp = await async_client.post(
        f"/api/v1/courses/topics/{topic_id}/objectives",
        json={
            "code": "LO_A",
            "title": "LO A",
            "description": "Base",
            "prerequisite_objective_ids": [],
        },
    )
    assert lo_a_resp.status_code == 201

    # 5. Create LO_B requiring LO_A (valid DAG dependency)
    lo_b_resp = await async_client.post(
        f"/api/v1/courses/topics/{topic_id}/objectives",
        json={
            "code": "LO_B",
            "title": "LO B",
            "description": "Child of A",
            "prerequisite_objective_ids": ["LO_A"],
        },
    )
    assert lo_b_resp.status_code == 201

    # 6. Cross-topic valid reference: Create Topic 2 in same course, LO_CROSS requiring LO_B
    t2_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/topics",
        json={"code": "TOPIC_2", "title": "Topic Two"},
    )
    topic_2_id = t2_resp.json()["id"]

    lo_cross_resp = await async_client.post(
        f"/api/v1/courses/topics/{topic_2_id}/objectives",
        json={
            "code": "LO_CROSS",
            "title": "Cross Topic LO",
            "description": "References LO_B from Topic 1",
            "prerequisite_objective_ids": ["LO_B"],
        },
    )
    assert lo_cross_resp.status_code == 201

    # 7. Cross-course isolation: Objective in another course cannot reference LO_A
    c2_resp = await async_client.post(
        "/api/v1/courses",
        json={"code": "OTHER_CS", "title": "Other Course"},
    )
    c2_id = c2_resp.json()["id"]
    t_other_resp = await async_client.post(
        f"/api/v1/courses/{c2_id}/topics",
        json={"code": "OTHER_TOPIC", "title": "Other Topic"},
    )
    t_other_id = t_other_resp.json()["id"]

    cross_course_resp = await async_client.post(
        f"/api/v1/courses/topics/{t_other_id}/objectives",
        json={
            "code": "LO_OUTSIDE",
            "title": "Outside Course Reference",
            "description": "Should fail",
            "prerequisite_objective_ids": ["LO_A"],
        },
    )
    assert cross_course_resp.status_code == 400
    assert cross_course_resp.json()["code"] == "UNRESOLVED_PREREQUISITE"


@pytest.mark.integration
async def test_arbitrary_length_prerequisite_cycle_rejected(
    async_client: AsyncClient, test_db_session: AsyncSession
) -> None:
    # 1. Create course and topic
    c_resp = await async_client.post(
        "/api/v1/courses",
        json={"code": "DAG_3_CS", "title": "DAG 3 Course"},
    )
    course_id = c_resp.json()["id"]

    t_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/topics",
        json={"code": "DAG_3_TOPIC", "title": "DAG 3 Topic"},
    )
    topic_id = t_resp.json()["id"]

    # 2. Directly prepare existing records in DB forming a chain:
    # LO_CHAIN_1 requires LO_CHAIN_2, LO_CHAIN_2 requires LO_CHAIN_3
    from app.models.curriculum import LearningObjective

    lo_1 = LearningObjective(
        topic_id=topic_id,
        code="LO_CHAIN_1",
        title="Chain 1",
        description="Chain node",
        order_index=1,
        prerequisite_objective_ids=["LO_CHAIN_2"],
        metadata_attributes={},
    )
    lo_2 = LearningObjective(
        topic_id=topic_id,
        code="LO_CHAIN_2",
        title="Chain 2",
        description="Chain node",
        order_index=2,
        prerequisite_objective_ids=["LO_CHAIN_3"],
        metadata_attributes={},
    )
    test_db_session.add_all([lo_1, lo_2])
    await test_db_session.commit()

    # 3. Client attempts to create LO_CHAIN_3 requiring LO_CHAIN_1
    # This forms a 3-node cycle: LO_CHAIN_1 -> LO_CHAIN_2 -> LO_CHAIN_3 -> LO_CHAIN_1
    cycle_resp = await async_client.post(
        f"/api/v1/courses/topics/{topic_id}/objectives",
        json={
            "code": "LO_CHAIN_3",
            "title": "Chain 3",
            "description": "Closes 3-node cycle",
            "prerequisite_objective_ids": ["LO_CHAIN_1"],
        },
    )
    assert cycle_resp.status_code == 400
    err = cycle_resp.json()
    assert err["code"] == "CYCLIC_PREREQUISITE"
    assert "LO_CHAIN_3 -> LO_CHAIN_1 -> LO_CHAIN_2 -> LO_CHAIN_3" in err["detail"]


@pytest.mark.integration
async def test_cross_topic_duplicate_code_ambiguity_and_uuid_resolution(
    async_client: AsyncClient,
) -> None:
    # 1. Create course and two distinct topics
    c_resp = await async_client.post(
        "/api/v1/courses",
        json={"code": "AMBIG_CS", "title": "Ambiguity Test Course"},
    )
    course_id = c_resp.json()["id"]

    t1_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/topics",
        json={"code": "TOPIC_A", "title": "Topic A"},
    )
    topic_a_id = t1_resp.json()["id"]

    t2_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/topics",
        json={"code": "TOPIC_B", "title": "Topic B"},
    )
    topic_b_id = t2_resp.json()["id"]

    # 2. Create LO_SHARED in Topic A
    lo_a_resp = await async_client.post(
        f"/api/v1/courses/topics/{topic_a_id}/objectives",
        json={
            "code": "LO_SHARED",
            "title": "Shared in A",
            "description": "Topic A variant",
            "prerequisite_objective_ids": [],
        },
    )
    assert lo_a_resp.status_code == 201
    lo_a_id = lo_a_resp.json()["id"]

    # 3. Create LO_SHARED in Topic B (permitted across distinct topics by schema)
    lo_b_resp = await async_client.post(
        f"/api/v1/courses/topics/{topic_b_id}/objectives",
        json={
            "code": "LO_SHARED",
            "title": "Shared in B",
            "description": "Topic B variant",
            "prerequisite_objective_ids": [],
        },
    )
    assert lo_b_resp.status_code == 201
    lo_b_id = lo_b_resp.json()["id"]

    # 4. Attempting to create duplicate LO_SHARED within Topic B fails with 409 Conflict
    dup_resp = await async_client.post(
        f"/api/v1/courses/topics/{topic_b_id}/objectives",
        json={
            "code": "LO_SHARED",
            "title": "Duplicate in B",
            "description": "Must fail",
            "prerequisite_objective_ids": [],
        },
    )
    assert dup_resp.status_code == 409
    assert dup_resp.json()["code"] == "OBJECTIVE_ALREADY_EXISTS"

    # 5. Referencing ambiguous code 'LO_SHARED' is rejected with 400 AMBIGUOUS_PREREQUISITE
    ambig_resp = await async_client.post(
        f"/api/v1/courses/topics/{topic_a_id}/objectives",
        json={
            "code": "LO_CONSUMER",
            "title": "Consumer",
            "description": "Uses ambiguous code",
            "prerequisite_objective_ids": ["LO_SHARED"],
        },
    )
    assert ambig_resp.status_code == 400
    assert ambig_resp.json()["code"] == "AMBIGUOUS_PREREQUISITE"

    # 6. Referencing specifically by UUID of Topic A's objective resolves cleanly
    res_a_resp = await async_client.post(
        f"/api/v1/courses/topics/{topic_a_id}/objectives",
        json={
            "code": "LO_CONSUMER_A",
            "title": "Consumer A",
            "description": "Uses Topic A UUID",
            "prerequisite_objective_ids": [lo_a_id],
        },
    )
    assert res_a_resp.status_code == 201

    # 7. Referencing specifically by UUID of Topic B's objective also resolves cleanly
    res_b_resp = await async_client.post(
        f"/api/v1/courses/topics/{topic_a_id}/objectives",
        json={
            "code": "LO_CONSUMER_B",
            "title": "Consumer B",
            "description": "Uses Topic B UUID",
            "prerequisite_objective_ids": [lo_b_id],
        },
    )
    assert res_b_resp.status_code == 201
