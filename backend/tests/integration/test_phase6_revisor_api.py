"""Integration tests for Phase 6 Grounded Revisor API, Abstention, and Assessment Lockout."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attempt import AssessmentContext, Attempt, AttemptStatus
from tests.auth_utils import create_authenticated_user


@pytest.mark.integration
async def test_phase6_revisor_api_lifecycle(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    # 0. Setup admin and student
    admin_user, admin_hdr = await create_authenticated_user(
        async_client, "admin@recall.edu", "Admin User", "admin"
    )
    student_user, student_hdr = await create_authenticated_user(
        async_client, "revisor_student@university.edu", "Revisor Student", "student"
    )
    student_id = student_user["id"]

    # 1. Seed courses and enroll student
    seed_resp = await async_client.post("/api/v1/courses/seed/dbms", headers=admin_hdr)
    assert seed_resp.status_code == 201
    course_id = seed_resp.json()["course_id"]

    enroll_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/enroll",
        json={"user_id": student_id, "course_id": course_id},
        headers=admin_hdr,
    )
    assert enroll_resp.status_code in (200, 201)

    # 2. Ingest course document for DBMS
    doc_text = (
        "Course Lecture 1: Relational Database Systems.\n\n"
        "Functional dependencies (FDs) represent semantic integrity constraints.\n\n"
        "Armstrong's Axioms provide a sound and complete inference system:\n"
        "1. Reflexivity: If Y is a subset of X, then X -> Y.\n"
        "2. Augmentation: If X -> Y, then XZ -> YZ.\n"
        "3. Transitivity: If X -> Y and Y -> Z, then X -> Z.\n\n"
        "Attribute Closure X+ is the set of all attributes functionally determined by X under F."
    )
    upload_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/documents/upload",
        files={"file": ("dbms_lecture1.txt", doc_text.encode("utf-8"), "text/plain")},
        headers=admin_hdr,
    )
    assert upload_resp.status_code == 201

    # 3. Grounded explanation audit: Valid grounded candidate text
    grounded_review_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/revisor/review",
        json={
            "student_id": student_id,
            "candidate_text": (
                "Armstrong's Axioms consist of reflexivity, augmentation, and transitivity. "
                "These axioms form a sound and complete inference system for "
                "functional dependencies."
            ),
            "query_or_topic": "Armstrong axioms and functional dependencies",
        },
        headers=student_hdr,
    )
    assert grounded_review_resp.status_code == 200
    rev_data = grounded_review_resp.json()
    assert rev_data["is_approved"] is True
    assert rev_data["audit_status"] == "verified_grounded"
    assert rev_data["retrieved_chunks_count"] > 0
    assert len(rev_data["citations_verified"]) > 0

    # 4. Ungrounded claim audit
    ungrounded_review_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/revisor/review",
        json={
            "student_id": student_id,
            "candidate_text": (
                "Functional dependencies require ungrounded quantum hashing and 6NF lattice models."
            ),
            "query_or_topic": "Functional dependencies",
        },
        headers=student_hdr,
    )
    assert ungrounded_review_resp.status_code == 200
    ungrounded_data = ungrounded_review_resp.json()
    assert ungrounded_data["audit_status"] == "ungrounded_claim_detected"
    assert ungrounded_data["is_approved"] is False

    # 5. Deterministic contradiction audit
    # Candidate text asserts that closure of {A} under A -> B is {A, B, C}
    contradiction_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/revisor/review",
        json={
            "student_id": student_id,
            "candidate_text": "The closure of {A} under A -> B is {A, B, C}.",
            "query_or_topic": "Functional dependencies and closure",
            "check_deterministic_logic": True,
        },
        headers=student_hdr,
    )
    assert contradiction_resp.status_code == 200
    contra_data = contradiction_resp.json()
    assert contra_data["audit_status"] == "contradiction_detected"
    assert contra_data["is_approved"] is False
    assert contra_data["deterministic_validation"]["contradiction_detected"] is True

    # 6. Abstention test for ungrounded / unsupported topic
    abstain_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/revisor/review",
        json={
            "student_id": student_id,
            "candidate_text": ("Photosynthesis occurs in chloroplasts using thylakoid membranes."),
            "query_or_topic": "Photosynthesis and cellular biology",
        },
        headers=student_hdr,
    )
    assert abstain_resp.status_code == 200
    abstain_data = abstain_resp.json()
    assert abstain_data["audit_status"] == "insufficient_evidence"
    assert abstain_data["abstention_recommended"] is True

    # 7. Non-negotiable architectural rule: Server-Side Scored Assessment Lockout
    # Create an active IN_PROGRESS attempt for the student
    topics_resp = await async_client.get(f"/api/v1/courses/{course_id}/topics")
    assert topics_resp.status_code == 200
    topic = topics_resp.json()[0]
    objective_id = topic["objectives"][0]["id"]

    q_resp = await async_client.get(f"/api/v1/questions/objective/{objective_id}")
    assert q_resp.status_code == 200
    target_q = q_resp.json()[0]

    active_att = Attempt(
        idempotency_key="lockout-revisor-test-key",
        student_id=student_id,
        question_id=target_q["id"],
        question_version_id=target_q["versions"][0]["id"],
        assessment_context=AssessmentContext.DIAGNOSTIC,
        submitted_answer={"status": "in_progress"},
        is_hint_assisted=False,
        hint_count=0,
        time_spent_ms=0,
        status=AttemptStatus.IN_PROGRESS,
        is_correct=False,
        score_achieved=0.0,
        max_possible_score=1.0,
        grading_provenance={},
    )
    test_db_session.add(active_att)
    await test_db_session.commit()

    # Revisor query MUST now fail with 403 Forbidden AssessmentLockoutError!
    locked_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/revisor/review",
        json={
            "student_id": student_id,
            "candidate_text": "Armstrong reflexivity allows trivial dependencies.",
            "query_or_topic": "Armstrong axioms",
        },
        headers=student_hdr,
    )
    assert locked_resp.status_code == 403
    lock_err = locked_resp.json()
    assert "lockout" in lock_err["title"].lower()
    assert lock_err["code"] == "ASSESSMENT_LOCKOUT"
    assert lock_err["status"] == 403
