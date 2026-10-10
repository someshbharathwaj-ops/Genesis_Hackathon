"""Integration tests for Phase 3: Evidence Representation and Bounded Diagnosis APIs."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_phase3_evidence_and_bounded_diagnosis_lifecycle(async_client: AsyncClient) -> None:
    # 1. Seed DBMS curriculum & verified question bank
    seed_resp = await async_client.post("/api/v1/courses/seed/dbms")
    assert seed_resp.status_code == 201
    course_id = seed_resp.json()["course_id"]

    # 2. Register student
    student_resp = await async_client.post(
        "/api/v1/users",
        json={
            "email": "student.phase3@recall.edu",
            "full_name": "Alan Turing",
            "role": "student",
        },
    )
    assert student_resp.status_code == 201
    student_id = student_resp.json()["id"]

    # Enroll student in course
    enroll_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/enroll",
        json={"user_id": student_id, "course_id": course_id},
    )
    assert enroll_resp.status_code == 201

    # 3. Query initial course diagnosis (all objectives UNTESTED)
    init_diag_resp = await async_client.get(
        f"/api/v1/diagnosis/student/{student_id}/course/{course_id}"
    )
    assert init_diag_resp.status_code == 200
    init_data = init_diag_resp.json()
    assert init_data["total_objectives"] == 5
    assert init_data["untested_count"] == 5
    assert init_data["mastered_count"] == 0
    assert init_data["demonstrated_weakness_count"] == 0
    assert init_data["average_performance"] == 0.0
    assert init_data["average_confidence"] == 0.0

    closure_obj = next(o for o in init_data["objectives"] if o["objective_code"] == "LO_CLOSURE")
    keys_obj = next(o for o in init_data["objectives"] if o["objective_code"] == "LO_KEYS")

    # 4. Query initial objective diagnosis for LO_CLOSURE
    closure_init_resp = await async_client.get(
        f"/api/v1/diagnosis/student/{student_id}/objective/{closure_obj['objective_id']}"
    )
    assert closure_init_resp.status_code == 200
    closure_init = closure_init_resp.json()
    assert closure_init["diagnostic_status"] == "untested"
    assert closure_init["sufficiency_status"] == "no_evidence"
    assert closure_init["recommended_action"] == "recommend_diagnostic_probe"
    assert len(closure_init["evidence_ledger"]["items"]) == 0

    # 5. Fetch questions for LO_CLOSURE
    q_resp = await async_client.get(f"/api/v1/questions/objective/{closure_obj['objective_id']}")
    assert q_resp.status_code == 200
    closure_questions = q_resp.json()
    assert len(closure_questions) >= 2

    q1_id = closure_questions[0]["id"]
    q2_id = closure_questions[1]["id"]

    # 6. Single failure test (Rule 2: Non-Catastrophic Diagnosis)
    # Student submits incorrect answer with missing attributes
    fail_1_resp = await async_client.post(
        "/api/v1/attempts",
        json={
            "student_id": student_id,
            "question_id": q1_id,
            "submitted_answer": {"closure": "A"},  # Missing B, C, D
            "is_hint_assisted": False,
            "assessment_context": "diagnostic",
        },
        headers={"Idempotency-Key": "phase3_idem_fail1"},
    )
    assert fail_1_resp.status_code == 201

    diag_after_single_fail_resp = await async_client.get(
        f"/api/v1/diagnosis/student/{student_id}/objective/{closure_obj['objective_id']}"
    )
    assert diag_after_single_fail_resp.status_code == 200
    single_fail_diag = diag_after_single_fail_resp.json()

    # Rule 2: Single failure MUST NOT trigger demonstrated_weakness
    assert single_fail_diag["diagnostic_status"] == "insufficient_evidence"
    assert single_fail_diag["sufficiency_status"] == "insufficient"
    assert single_fail_diag["confidence_score"] < 0.50

    # Misconception must be candidate_signal, not confirmed
    assert len(single_fail_diag["confirmed_misconceptions"]) == 0
    assert len(single_fail_diag["candidate_signals"]) >= 1
    assert single_fail_diag["candidate_signals"][0]["status"] == "candidate_signal"
    assert "Missing attributes" in single_fail_diag["candidate_signals"][0]["signature"]
    assert single_fail_diag["recommended_action"] == "recommend_diagnostic_probe"

    # 7. Second distinct failure test -> transitions to demonstrated_weakness
    # and confirmed misconception
    fail_2_resp = await async_client.post(
        "/api/v1/attempts",
        json={
            "student_id": student_id,
            "question_id": q2_id,
            "submitted_answer": {"closure": "X"},
            "is_hint_assisted": False,
            "assessment_context": "diagnostic",
        },
        headers={"Idempotency-Key": "phase3_idem_fail2"},
    )
    assert fail_2_resp.status_code == 201

    diag_after_two_fails_resp = await async_client.get(
        f"/api/v1/diagnosis/student/{student_id}/objective/{closure_obj['objective_id']}"
    )
    assert diag_after_two_fails_resp.status_code == 200
    two_fails_diag = diag_after_two_fails_resp.json()

    # Sufficient evidence (2 distinct items) -> demonstrated_weakness
    assert two_fails_diag["diagnostic_status"] == "demonstrated_weakness"
    assert two_fails_diag["sufficiency_status"] == "sufficient"
    assert two_fails_diag["confidence_score"] >= 0.50
    assert len(two_fails_diag["confirmed_misconceptions"]) >= 1
    assert two_fails_diag["confirmed_misconceptions"][0]["status"] == "confirmed_misconception"

    # 8. Check prerequisite attribution for child objective LO_KEYS
    # LO_KEYS has prerequisite LO_CLOSURE.
    keys_diag_resp = await async_client.get(
        f"/api/v1/diagnosis/student/{student_id}/objective/{keys_obj['objective_id']}"
    )
    assert keys_diag_resp.status_code == 200
    keys_diag = keys_diag_resp.json()
    assert not keys_diag["prerequisites_satisfied"]
    assert any(
        t["prerequisite_code"] == "LO_CLOSURE" and not t["is_satisfied"]
        for t in keys_diag["prerequisite_traces"]
    )
    assert keys_diag["recommended_action"] == "recommend_prerequisite_remediation"

    # 9. Test Diagnostic Session Planner
    session_plan_resp = await async_client.post(
        "/api/v1/diagnosis/session/plan",
        json={
            "student_id": student_id,
            "course_id": course_id,
            "target_objective_id": keys_obj["objective_id"],
        },
    )
    assert session_plan_resp.status_code == 200
    plan_data = session_plan_resp.json()
    assert plan_data["max_session_questions"] == 5
    assert len(plan_data["recommended_questions"]) <= 5
    assert len(plan_data["recommended_questions"]) > 0

    # Prerequisite probe should be prioritized
    first_q = plan_data["recommended_questions"][0]
    assert "Prerequisite" in first_q["priority_reason"] or "LO_CLOSURE" in first_q["objective_code"]

    # 10. Negative tests: non-existent resource lookups
    bad_student_resp = await async_client.get(
        f"/api/v1/diagnosis/student/bad_id/course/{course_id}"
    )
    assert bad_student_resp.status_code == 404
    assert bad_student_resp.json()["code"] == "RESOURCE_NOT_FOUND"

    bad_course_resp = await async_client.get(
        f"/api/v1/diagnosis/student/{student_id}/course/bad_course_id"
    )
    assert bad_course_resp.status_code == 404
    assert bad_course_resp.json()["code"] == "RESOURCE_NOT_FOUND"

    bad_obj_resp = await async_client.get(
        f"/api/v1/diagnosis/student/{student_id}/objective/bad_obj_id"
    )
    assert bad_obj_resp.status_code == 404
    assert bad_obj_resp.json()["code"] == "RESOURCE_NOT_FOUND"
