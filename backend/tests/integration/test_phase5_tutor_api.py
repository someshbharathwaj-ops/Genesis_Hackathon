"""Integration tests for Phase 5: Grounded Tutor API, Course Isolation, and Assessment Lockout."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.auth_utils import create_authenticated_user


@pytest.mark.integration
async def test_phase5_grounded_tutor_api_lifecycle(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    # 0. Setup admin and student
    admin_user, admin_hdr = await create_authenticated_user(
        async_client, "admin@recall.edu", "Admin User", "admin"
    )
    student_user, student_hdr = await create_authenticated_user(
        async_client, "tutor_student@university.edu", "Tutor Student", "student"
    )
    student_id = student_user["id"]

    # 1. Seed courses and learning objectives
    seed_resp = await async_client.post("/api/v1/courses/seed/dbms", headers=admin_hdr)
    assert seed_resp.status_code == 201
    course_id = seed_resp.json()["course_id"]

    # Enroll student in course
    enroll_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/enroll",
        json={"user_id": student_id, "course_id": course_id},
        headers=admin_hdr,
    )
    assert enroll_resp.status_code in (200, 201)

    # 2. Ingest course document for Course 1 (DBMS)
    doc_text = (
        "Course Lecture 1: Relational Database Systems.\n\n"
        "Functional dependencies (FDs) represent semantic integrity constraints.\n\n"
        "Armstrong's Axioms provide a sound and complete inference system:\n"
        "1. Reflexivity: If Y is a subset of X, then X -> Y.\n"
        "2. Augmentation: If X -> Y, then XZ -> YZ.\n"
        "3. Transitivity: If X -> Y and Y -> Z, then X -> Z.\n\n"
        "Attribute Closure X+ is the set of all attributes functionally determined by X."
    )
    upload_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/documents/upload",
        files={"file": ("dbms_lecture1.txt", doc_text.encode("utf-8"), "text/plain")},
        headers=admin_hdr,
    )
    assert upload_resp.status_code == 201
    assert upload_resp.json()["status"] == "indexed"

    # 3. Grounded Tutor Query: Relevant syllabus concept inquiry
    tutor_query_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/tutor/ask",
        json={
            "student_id": student_id,
            "query": "Can you explain Armstrong's Axioms and transitivity?",
        },
        headers=student_hdr,
    )
    assert tutor_query_resp.status_code == 200
    tutor_data = tutor_query_resp.json()
    assert not tutor_data["abstention_recommended"]
    assert tutor_data["retrieved_chunks_count"] > 0
    assert len(tutor_data["citations"]) > 0
    assert any("[Lecture: dbms_lecture1.txt, Page 1]" in c for c in tutor_data["citations"])
    assert "Armstrong" in tutor_data["answer"]

    # 4. Irrelevant Query / Abstention Test
    irrelevant_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/tutor/ask",
        json={
            "student_id": student_id,
            "query": "What is the function of the ribosome in protein synthesis?",
        },
        headers=student_hdr,
    )
    assert irrelevant_resp.status_code == 200
    irrelevant_data = irrelevant_resp.json()
    assert irrelevant_data["abstention_recommended"]
    assert irrelevant_data["citations"] == []
    assert "abstaining" in irrelevant_data["answer"].lower()

    # 5. Course Isolation Test
    # Create second course (CS401) and upload OS notes
    course2_resp = await async_client.post(
        "/api/v1/courses",
        json={
            "code": "CS401",
            "title": "Operating Systems",
            "description": "Kernel architectures",
        },
        headers=admin_hdr,
    )
    assert course2_resp.status_code == 201
    course2_id = course2_resp.json()["id"]

    os_text = "Virtual memory paging: Page tables, TLB cache, and FIFO page replacement."
    upload2_resp = await async_client.post(
        f"/api/v1/courses/{course2_id}/documents/upload",
        files={"file": ("os_lecture1.txt", os_text.encode("utf-8"), "text/plain")},
        headers=admin_hdr,
    )
    assert upload2_resp.status_code == 201

    # Ask DBMS Course 1 tutor about OS virtual memory paging
    cross_course_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/tutor/ask",
        json={
            "student_id": student_id,
            "query": "Explain virtual memory paging and TLB cache",
        },
        headers=student_hdr,
    )
    assert cross_course_resp.status_code == 200
    cross_data = cross_course_resp.json()
    # DBMS tutor must abstain because OS notes are in Course 2
    assert cross_data["abstention_recommended"]
    assert all("os_lecture1.txt" not in c for c in cross_data["citations"])

    # 6. Server-Side Scored Assessment Lockout
    # Fetch topics and objectives for DBMS
    topics_resp = await async_client.get(f"/api/v1/courses/{course_id}/topics")
    assert topics_resp.status_code == 200
    topic = topics_resp.json()[0]
    objective_id = topic["objectives"][0]["id"]

    questions_resp = await async_client.get(f"/api/v1/questions/objective/{objective_id}")
    assert questions_resp.status_code == 200
    questions = questions_resp.json()
    assert len(questions) > 0
    question_id = questions[0]["id"]
    question_ver_id = questions[0]["versions"][0]["id"]

    # Create an attempt with IN_PROGRESS status to trigger server-side lockout
    from app.models.attempt import AssessmentContext, Attempt, AttemptStatus

    in_progress_attempt = Attempt(
        idempotency_key="test_lockout_attempt_1",
        student_id=student_id,
        question_id=question_id,
        question_version_id=question_ver_id,
        assessment_context=AssessmentContext.DIAGNOSTIC,
        submitted_answer={"answer": "in progress work"},
        status=AttemptStatus.IN_PROGRESS,
        is_hint_assisted=False,
        hint_count=0,
        time_spent_ms=1000,
        is_correct=False,
        score_achieved=0.0,
        max_possible_score=1.0,
        grading_provenance={},
    )
    test_db_session.add(in_progress_attempt)
    await test_db_session.commit()

    # While assessment is in progress, tutor request must be blocked with 403
    locked_tutor_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/tutor/ask",
        json={
            "student_id": student_id,
            "query": "Can you help me solve this diagnostic question?",
        },
        headers=student_hdr,
    )
    assert locked_tutor_resp.status_code == 403
    lock_error = locked_tutor_resp.json()
    assert lock_error["code"] == "ASSESSMENT_LOCKOUT"
    assert "lockout" in lock_error["title"].lower()

    # 7. Validation: Short query rejection
    short_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/tutor/ask",
        json={
            "student_id": student_id,
            "query": "hi",
        },
        headers=student_hdr,
    )
    assert short_resp.status_code == 422
