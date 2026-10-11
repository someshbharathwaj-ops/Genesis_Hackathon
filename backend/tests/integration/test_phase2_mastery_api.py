"""Integration tests for Phase 2: Deterministic DBMS Grader and Mastery Engine APIs."""

import pytest
from httpx import AsyncClient

from tests.auth_utils import create_authenticated_user


@pytest.mark.integration
async def test_phase2_dbms_grading_and_mastery_lifecycle(async_client: AsyncClient) -> None:
    # 1. Seed DBMS curriculum & verified question bank via instructor
    _, inst_hdr = await create_authenticated_user(
        async_client, "inst.phase2@recall.edu", "Prof DBMS", "instructor"
    )
    seed_resp = await async_client.post("/api/v1/courses/seed/dbms", headers=inst_hdr)
    assert seed_resp.status_code == 201
    course_id = seed_resp.json()["course_id"]

    # 2. Register a new student
    student_data, student_hdr = await create_authenticated_user(
        async_client, "student.phase2@recall.edu", "Ada Lovelace", "student"
    )
    student_id = student_data["id"]

    # Enroll student in course
    enroll_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/enroll",
        json={"user_id": student_id, "course_id": course_id},
        headers=student_hdr,
    )
    assert enroll_resp.status_code == 201

    # 3. Query initial course mastery (should be 100% UNTESTED)
    init_mastery_resp = await async_client.get(
        f"/api/v1/mastery/student/{student_id}/course/{course_id}",
        headers=student_hdr,
    )
    assert init_mastery_resp.status_code == 200
    init_data = init_mastery_resp.json()
    assert init_data["total_objectives"] == 5
    assert init_data["untested_count"] == 5
    assert init_data["average_performance"] == 0.0
    assert init_data["average_confidence"] == 0.0

    # 4. Fetch questions to find LO_CLOSURE items
    closure_prof = next(p for p in init_data["objectives"] if p["objective_code"] == "LO_CLOSURE")
    questions_resp = await async_client.get(
        f"/api/v1/questions/objective/{closure_prof['objective_id']}"
    )
    assert questions_resp.status_code == 200
    closure_questions = questions_resp.json()
    assert len(closure_questions) >= 2

    # 5. Submit correct attempt for Question 1
    q1 = closure_questions[0]
    att1_resp = await async_client.post(
        "/api/v1/attempts",
        json={
            "student_id": student_id,
            "question_id": q1["id"],
            "submitted_answer": {"closure": "A, B, C, D"},
            "is_hint_assisted": False,
            "hint_count": 0,
            "time_spent_ms": 3200,
            "assessment_context": "diagnostic",
        },
        headers={"Idempotency-Key": "phase2_test_att1_key", **student_hdr},
    )
    assert att1_resp.status_code == 201
    att1_data = att1_resp.json()
    assert att1_data["is_correct"] is True
    assert att1_data["score_achieved"] == 1.0
    assert att1_data["grading_provenance"]["rubric_type"] == "attribute_closure"

    # 6. Submit correct attempt for Question 2
    q2 = closure_questions[1]
    att2_resp = await async_client.post(
        "/api/v1/attempts",
        json={
            "student_id": student_id,
            "question_id": q2["id"],
            "submitted_answer": {"closure": "A, B, C, D, E"},
            "is_hint_assisted": False,
            "hint_count": 0,
            "time_spent_ms": 4500,
            "assessment_context": "diagnostic",
        },
        headers={"Idempotency-Key": "phase2_test_att2_key", **student_hdr},
    )
    assert att2_resp.status_code == 201
    assert att2_resp.json()["is_correct"] is True

    # 7. Check Objective Mastery for LO_CLOSURE
    lo_closure_id = q1["objective_id"]
    lo_mastery_resp = await async_client.get(
        f"/api/v1/mastery/student/{student_id}/objective/{lo_closure_id}",
        headers=student_hdr,
    )
    assert lo_mastery_resp.status_code == 200
    lo_data = lo_mastery_resp.json()
    assert lo_data["performance_score"] == 1.0
    assert lo_data["confidence_score"] >= 0.66
    assert lo_data["mastery_state"] == "mastered"
    assert lo_data["prerequisites_satisfied"] is True

    # 8. Check Updated Course Mastery
    updated_mastery_resp = await async_client.get(
        f"/api/v1/mastery/student/{student_id}/course/{course_id}",
        headers=student_hdr,
    )
    assert updated_mastery_resp.status_code == 200
    updated_data = updated_mastery_resp.json()
    assert updated_data["mastered_count"] == 1
    assert updated_data["average_performance"] > 0.0
    assert updated_data["average_confidence"] > 0.0
