"""Integration tests for Phase 6 Spaced Retention Scheduling API."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
async def test_phase6_scheduling_api_lifecycle(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
) -> None:
    # 1. Seed course and create student
    seed_resp = await async_client.post("/api/v1/courses/seed/dbms")
    assert seed_resp.status_code == 201
    course_id = seed_resp.json()["course_id"]

    user_resp = await async_client.post(
        "/api/v1/users",
        json={
            "email": "sched_student@university.edu",
            "full_name": "Scheduling Student",
            "role": "student",
        },
    )
    assert user_resp.status_code == 201
    student_id = user_resp.json()["id"]

    # 2. Get initial review queue (all objectives untested)
    queue_resp = await async_client.get(
        f"/api/v1/courses/{course_id}/scheduling/student/{student_id}/review-queue"
    )
    assert queue_resp.status_code == 200
    queue_data = queue_resp.json()
    assert queue_data["student_id"] == student_id
    assert queue_data["course_id"] == course_id
    assert queue_data["total_objectives_evaluated"] > 0
    assert all(it["mastery_state"] == "untested" for it in queue_data["items"])

    # 3. Submit a scored attempt on a question in the course
    target_lo_id = queue_data["items"][0]["objective_id"]
    q_resp = await async_client.get(f"/api/v1/questions/objective/{target_lo_id}")
    assert q_resp.status_code == 200
    questions = q_resp.json()
    assert len(questions) > 0
    target_q = questions[0]
    att_resp = await async_client.post(
        "/api/v1/attempts",
        json={
            "student_id": student_id,
            "question_id": target_q["id"],
            "submitted_answer": {"closure": "A, B, C, D"},
            "is_hint_assisted": False,
            "hint_count": 0,
            "time_spent_ms": 15000,
            "assessment_context": "diagnostic",
        },
        headers={"Idempotency-Key": "idem-sched-att-1"},
    )
    assert att_resp.status_code == 201

    # 4. Check Review Queue: Rule 6 Working Memory Lockout Active
    # An attempt made just now must be in working memory (< 3600s)
    queue2_resp = await async_client.get(
        f"/api/v1/courses/{course_id}/scheduling/student/{student_id}/review-queue"
    )
    assert queue2_resp.status_code == 200
    queue2_data = queue2_resp.json()
    assert queue2_data["working_memory_locked_count"] >= 1

    locked_items = [it for it in queue2_data["items"] if it["in_working_memory"]]
    assert len(locked_items) >= 1
    assert locked_items[0]["retention_eligible"] is False
    assert locked_items[0]["urgency_classification"] == "cooldown_locked"
    assert locked_items[0]["urgency_score"] == 0.0

    # 5. Plan session with default cooldown: working memory locked item is NOT included
    plan_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/scheduling/student/{student_id}/plan-session",
        json={"max_items": 5},
    )
    assert plan_resp.status_code == 200
    plan_data = plan_resp.json()
    assert plan_data["context"] == "retention_review"
    assert all(not it["in_working_memory"] for it in plan_data["planned_items"])

    # 6. Override cooldown with 0.0s (simulating cooldown elapsed):
    # The item becomes retention eligible!
    queue_unlocked_resp = await async_client.get(
        f"/api/v1/courses/{course_id}/scheduling/student/{student_id}/review-queue",
        params={"cooldown_seconds": 0.0},
    )
    assert queue_unlocked_resp.status_code == 200
    queue_unlocked_data = queue_unlocked_resp.json()
    unlocked_target = next(
        it for it in queue_unlocked_data["items"] if it["objective_id"] == target_q["objective_id"]
    )
    assert unlocked_target["in_working_memory"] is False
    assert unlocked_target["retention_eligible"] is True

    # 7. Invalid course / user 404 checks
    bad_course_resp = await async_client.get(
        f"/api/v1/courses/non-existent-course-id/scheduling/student/{student_id}/review-queue"
    )
    assert bad_course_resp.status_code == 404

    bad_user_resp = await async_client.get(
        f"/api/v1/courses/{course_id}/scheduling/student/non-existent-user-id/review-queue"
    )
    assert bad_user_resp.status_code == 404
