"""Integration and contract tests for Phase 1 identity,
courses, versioned questions, and idempotent attempts.
"""

import pytest
from httpx import AsyncClient


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
        headers={"Idempotency-Key": idem_key},
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
        headers={"Idempotency-Key": idem_key},
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
        headers={"Idempotency-Key": idem_key},
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
        headers={"Idempotency-Key": "hint-att-001"},
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
        headers={"Idempotency-Key": "repeat-att-002"},
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
        headers={"Idempotency-Key": "unverified-att-001"},
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
    )
    assert enroll_resp.status_code == 201

    # Re-enroll returns existing 201/200
    re_enroll = await async_client.post(
        f"/api/v1/courses/{first_course_id}/enroll",
        json={"user_id": first_user_id, "course_id": first_course_id},
    )
    assert re_enroll.status_code == 201

    # 6. Not found negative tests
    assert (await async_client.get("/api/v1/users/nonexistent-user")).status_code == 404
    assert (await async_client.get("/api/v1/courses/nonexistent-course")).status_code == 404
    assert (await async_client.get("/api/v1/questions/nonexistent-q")).status_code == 404
    assert (await async_client.get("/api/v1/attempts/nonexistent-att")).status_code == 404

