"""Unit tests for the Deterministic Spaced Retention Scheduling Engine."""

from datetime import UTC, datetime, timedelta

from app.models.attempt import AssessmentContext, Attempt, AttemptStatus
from app.models.curriculum import LearningObjective
from app.modules.adaptive_learning.mastery_engine import (
    MasteryState,
    ObjectiveMasteryProfile,
)
from app.modules.adaptive_learning.scheduling_engine import (
    ReviewUrgency,
    SchedulingEngine,
)


def _create_mock_lo(lo_id: str = "lo-1", code: str = "DBMS-FD-01") -> LearningObjective:
    return LearningObjective(
        id=lo_id,
        topic_id="topic-1",
        code=code,
        title="Functional Dependencies",
        description="Understanding FDs and Armstrong axioms",
        order_index=1,
    )


def _create_mock_attempt(
    attempt_id: str,
    question_id: str,
    is_correct: bool,
    is_hint_assisted: bool,
    created_at: datetime,
) -> Attempt:
    return Attempt(
        id=attempt_id,
        idempotency_key=f"idem-{attempt_id}",
        student_id="student-1",
        question_id=question_id,
        question_version_id="qv-1",
        assessment_context=AssessmentContext.DIAGNOSTIC,
        submitted_answer={"answer": "valid"},
        is_hint_assisted=is_hint_assisted,
        hint_count=1 if is_hint_assisted else 0,
        time_spent_ms=10000,
        submitted_at=created_at,
        created_at=created_at,
        status=AttemptStatus.GRADED,
        is_correct=is_correct,
        score_achieved=1.0 if is_correct else 0.0,
        max_possible_score=1.0,
        grading_provenance={"checks": []},
    )


def test_scheduling_untested_objective() -> None:
    lo = _create_mock_lo()
    prof = ObjectiveMasteryProfile(
        objective_id=lo.id,
        objective_code=lo.code,
        performance_score=0.0,
        confidence_score=0.0,
        mastery_state=MasteryState.UNTESTED,
        prerequisites_satisfied=True,
    )

    sched = SchedulingEngine.compute_objective_schedule(
        objective=lo,
        attempts=[],
        mastery_profile=prof,
    )

    assert sched.urgency_classification == ReviewUrgency.UNTESTED
    assert sched.retention_eligible is False
    assert sched.in_working_memory is False


def test_rule_6_working_memory_cooldown_enforcement() -> None:
    """Rule 6: Attempts within working memory cooldown must be locked out from retention retest."""
    now = datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
    recent_time = now - timedelta(minutes=15)  # 15 minutes ago (< 1 hour cooldown)

    lo = _create_mock_lo()
    att = _create_mock_attempt("att-1", "q-1", True, False, recent_time)

    prof = ObjectiveMasteryProfile(
        objective_id=lo.id,
        objective_code=lo.code,
        performance_score=1.0,
        confidence_score=0.8,
        mastery_state=MasteryState.MASTERED,
        prerequisites_satisfied=True,
    )

    sched = SchedulingEngine.compute_objective_schedule(
        objective=lo,
        attempts=[att],
        mastery_profile=prof,
        as_of_time=now,
        cooldown_seconds=3600.0,
    )

    # In working memory!
    assert sched.in_working_memory is True
    assert sched.retention_eligible is False
    assert sched.urgency_classification == ReviewUrgency.COOLDOWN_LOCKED
    assert sched.urgency_score == 0.0
    assert "Working memory cooldown active" in sched.recommended_action


def test_overdue_retention_scheduling() -> None:
    now = datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
    old_time = now - timedelta(days=10)

    lo = _create_mock_lo()
    att = _create_mock_attempt("att-1", "q-1", True, False, old_time)

    prof = ObjectiveMasteryProfile(
        objective_id=lo.id,
        objective_code=lo.code,
        performance_score=0.7,
        confidence_score=0.6,
        mastery_state=MasteryState.DEVELOPING,
        prerequisites_satisfied=True,
    )

    sched = SchedulingEngine.compute_objective_schedule(
        objective=lo,
        attempts=[att],
        mastery_profile=prof,
        as_of_time=now,
        cooldown_seconds=3600.0,
    )

    assert sched.in_working_memory is False
    assert sched.retention_eligible is True
    assert sched.urgency_classification == ReviewUrgency.OVERDUE
    assert sched.urgency_score > 0.7
    assert sched.estimated_retention < 0.5


def test_consecutive_successes_expand_retention_interval() -> None:
    now = datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
    t1 = now - timedelta(days=20)
    t2 = now - timedelta(days=15)
    t3 = now - timedelta(days=10)

    lo = _create_mock_lo()
    atts = [
        _create_mock_attempt("att-1", "q-1", True, False, t1),
        _create_mock_attempt("att-2", "q-2", True, False, t2),
        _create_mock_attempt("att-3", "q-3", True, False, t3),
    ]

    prof = ObjectiveMasteryProfile(
        objective_id=lo.id,
        objective_code=lo.code,
        performance_score=1.0,
        confidence_score=1.0,
        mastery_state=MasteryState.MASTERED,
        prerequisites_satisfied=True,
    )

    sched = SchedulingEngine.compute_objective_schedule(
        objective=lo,
        attempts=atts,
        mastery_profile=prof,
        as_of_time=now,
    )

    assert sched.interval_days >= 10.0
    assert sched.retention_stability_days >= 8.0


def test_build_review_queue_ordering() -> None:
    now = datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)

    # Item 1: Overdue
    lo1 = _create_mock_lo("lo-1", "DBMS-01")
    item_overdue = SchedulingEngine.compute_objective_schedule(
        objective=lo1,
        attempts=[_create_mock_attempt("a1", "q1", True, False, now - timedelta(days=15))],
        mastery_profile=ObjectiveMasteryProfile(
            "lo-1", "DBMS-01", 0.7, 0.6, MasteryState.DEVELOPING, True
        ),
        as_of_time=now,
    )

    # Item 2: Working memory locked (10 mins ago)
    lo2 = _create_mock_lo("lo-2", "DBMS-02")
    item_locked = SchedulingEngine.compute_objective_schedule(
        objective=lo2,
        attempts=[_create_mock_attempt("a2", "q2", True, False, now - timedelta(minutes=10))],
        mastery_profile=ObjectiveMasteryProfile(
            "lo-2", "DBMS-02", 0.9, 0.9, MasteryState.MASTERED, True
        ),
        as_of_time=now,
    )

    # Item 3: Untested
    lo3 = _create_mock_lo("lo-3", "DBMS-03")
    item_untested = SchedulingEngine.compute_objective_schedule(
        objective=lo3,
        attempts=[],
        mastery_profile=ObjectiveMasteryProfile(
            "lo-3", "DBMS-03", 0.0, 0.0, MasteryState.UNTESTED, True
        ),
        as_of_time=now,
    )

    queue = SchedulingEngine.build_review_queue(
        student_id="student-1",
        course_id="course-1",
        items=[item_locked, item_untested, item_overdue],
        as_of_time=now,
    )

    assert queue.total_objectives_evaluated == 3
    assert queue.overdue_count == 1
    assert queue.working_memory_locked_count == 1
    # Overdue must be first in queue
    assert queue.items[0].objective_id == "lo-1"
    # Cooldown locked must be placed at the end
    assert queue.items[-1].objective_id == "lo-2"


def test_plan_retention_session_excludes_cooldown_locked_items() -> None:
    now = datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)

    lo1 = _create_mock_lo("lo-1", "DBMS-01")
    item_overdue = SchedulingEngine.compute_objective_schedule(
        objective=lo1,
        attempts=[_create_mock_attempt("a1", "q1", True, False, now - timedelta(days=15))],
        mastery_profile=ObjectiveMasteryProfile(
            "lo-1", "DBMS-01", 0.7, 0.6, MasteryState.DEVELOPING, True
        ),
        as_of_time=now,
    )

    lo2 = _create_mock_lo("lo-2", "DBMS-02")
    item_locked = SchedulingEngine.compute_objective_schedule(
        objective=lo2,
        attempts=[_create_mock_attempt("a2", "q2", True, False, now - timedelta(minutes=5))],
        mastery_profile=ObjectiveMasteryProfile(
            "lo-2", "DBMS-02", 0.9, 0.9, MasteryState.MASTERED, True
        ),
        as_of_time=now,
    )

    queue = SchedulingEngine.build_review_queue(
        student_id="student-1",
        course_id="course-1",
        items=[item_locked, item_overdue],
        as_of_time=now,
    )

    plan = SchedulingEngine.plan_retention_session(queue, max_session_items=5)

    assert plan.context == AssessmentContext.RETENTION_REVIEW
    assert plan.total_items == 1
    assert plan.planned_items[0].objective_id == "lo-1"
    # Cooldown item MUST NOT be in the planned session!
    assert all(it.objective_id != "lo-2" for it in plan.planned_items)
