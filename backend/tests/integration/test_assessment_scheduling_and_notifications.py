"""Integration test for Teacher Assessment Scheduling and Student In-App Notifications."""

from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

from tests.auth_utils import create_authenticated_user


@pytest.mark.integration
async def test_assessment_scheduling_and_student_notifications(async_client: AsyncClient) -> None:
    # 1. Create Instructor and Seed DBMS Course
    _, inst_hdr = await create_authenticated_user(
        async_client, "prof.sched@recall.edu", "Prof Sched", "instructor"
    )
    seed_resp = await async_client.post("/api/v1/courses/seed/dbms", headers=inst_hdr)
    assert seed_resp.status_code == 201
    course_id = seed_resp.json()["course_id"]

    # 2. Create Enrolled Student A and Student B
    student_a_data, student_a_hdr = await create_authenticated_user(
        async_client, "alice.sched@recall.edu", "Alice Student", "student"
    )
    student_b_data, student_b_hdr = await create_authenticated_user(
        async_client, "bob.sched@recall.edu", "Bob Student", "student"
    )

    # Enroll Alice in course
    enroll_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/enroll",
        json={"user_id": student_a_data["id"], "course_id": course_id},
        headers=student_a_hdr,
    )
    assert enroll_resp.status_code == 201

    # 3. Instructor schedules an assessment
    sched_payload = {
        "title": "Midterm Examination on Normalization & Closures",
        "description": "Comprehensive timed quiz covering 1NF-BCNF and functional dependencies.",
        "scheduled_at": datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc).isoformat(),
        "duration_minutes": 45,
    }
    sched_resp = await async_client.post(
        f"/api/v1/courses/{course_id}/assessments",
        json=sched_payload,
        headers=inst_hdr,
    )
    assert sched_resp.status_code == 201
    assessment = sched_resp.json()
    assert assessment["title"] == sched_payload["title"]
    assert assessment["status"] == "scheduled"
    assert assessment["duration_minutes"] == 45

    # 4. Enrolled student (Alice) lists course assessments
    list_resp = await async_client.get(
        f"/api/v1/courses/{course_id}/assessments",
        headers=student_a_hdr,
    )
    assert list_resp.status_code == 200
    assessments_list = list_resp.json()
    assert len(assessments_list) >= 1
    assert any(a["id"] == assessment["id"] for a in assessments_list)

    # 5. Alice checks in-app notifications
    notifs_resp = await async_client.get(
        f"/api/v1/students/{student_a_data['id']}/notifications",
        headers=student_a_hdr,
    )
    assert notifs_resp.status_code == 200
    alice_notifs = notifs_resp.json()
    assert len(alice_notifs) >= 1
    target_notif = next(n for n in alice_notifs if n["assessment_id"] == assessment["id"])
    assert "Midterm Examination" in target_notif["title"]
    assert not target_notif["is_read"]

    # 6. Alice marks notification as read
    read_resp = await async_client.post(
        f"/api/v1/students/{student_a_data['id']}/notifications/{target_notif['id']}/read",
        headers=student_a_hdr,
    )
    assert read_resp.status_code == 200
    assert read_resp.json()["is_read"] is True

    # 7. Unenrolled Student B (Bob) checks his notifications - should NOT have notification for this course
    bob_notifs_resp = await async_client.get(
        f"/api/v1/students/{student_b_data['id']}/notifications",
        headers=student_b_hdr,
    )
    assert bob_notifs_resp.status_code == 200
    bob_notifs = bob_notifs_resp.json()
    assert not any(n.get("assessment_id") == assessment["id"] for n in bob_notifs)

    # 8. Security test: Bob cannot read Alice's notifications (returns 403 Forbidden)
    forbidden_resp = await async_client.get(
        f"/api/v1/students/{student_a_data['id']}/notifications",
        headers=student_b_hdr,
    )
    assert forbidden_resp.status_code == 403
