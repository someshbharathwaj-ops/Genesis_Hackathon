"""Unit tests for the Deterministic MasteryEngine."""

from datetime import UTC, datetime

import pytest

from app.models.attempt import AssessmentContext, Attempt, AttemptStatus
from app.models.curriculum import LearningObjective
from app.modules.adaptive_learning.mastery_engine import (
    MasteryEngine,
    MasteryState,
    ObjectiveMasteryProfile,
)


def _make_attempt(
    question_id: str,
    score: float,
    max_score: float = 1.0,
    is_hint_assisted: bool = False,
    hint_count: int = 0,
) -> Attempt:
    return Attempt(
        idempotency_key=f"key_{question_id}_{score}_{datetime.now(UTC).timestamp()}",
        student_id="student-1",
        question_id=question_id,
        question_version_id="ver-1",
        assessment_context=AssessmentContext.DIAGNOSTIC,
        submitted_answer={"val": "ans"},
        is_hint_assisted=is_hint_assisted,
        hint_count=hint_count,
        time_spent_ms=1000,
        submitted_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        status=AttemptStatus.GRADED,
        is_correct=score == max_score,
        score_achieved=score,
        max_possible_score=max_score,
        grading_provenance={},
    )


@pytest.mark.unit
def test_mastery_untested() -> None:
    lo = LearningObjective(
        id="lo-1",
        topic_id="t-1",
        code="LO_CLOSURE",
        title="Closure",
        description="",
        order_index=1,
        prerequisite_objective_ids=[],
    )
    prof = MasteryEngine.compute_objective_mastery(lo, attempts=[])

    assert prof.mastery_state == MasteryState.UNTESTED
    assert prof.performance_score == 0.0
    assert prof.confidence_score == 0.0
    assert prof.total_attempts == 0


@pytest.mark.unit
def test_mastery_insufficient_evidence_and_non_catastrophic_failure() -> None:
    lo = LearningObjective(
        id="lo-1",
        topic_id="t-1",
        code="LO_CLOSURE",
        title="Closure",
        description="",
        order_index=1,
        prerequisite_objective_ids=[],
    )
    # 1 failed attempt: Rule 2 specifies single failure must not cause catastrophic collapse
    att = _make_attempt(question_id="q-1", score=0.0)
    prof = MasteryEngine.compute_objective_mastery(lo, attempts=[att])

    assert prof.mastery_state == MasteryState.INSUFFICIENT_EVIDENCE
    assert prof.performance_score == 0.0
    assert prof.confidence_score == 0.3333  # 1/3 volume
    assert prof.confidence_score < MasteryEngine.CONFIDENCE_THRESHOLD


@pytest.mark.unit
def test_mastery_developing_state() -> None:
    lo = LearningObjective(
        id="lo-1",
        topic_id="t-1",
        code="LO_KEYS",
        title="Keys",
        description="",
        order_index=1,
        prerequisite_objective_ids=[],
    )
    # 2 distinct questions: 1.0 and 0.5 -> avg 0.75, confidence 2/3 = 0.67
    atts = [
        _make_attempt(question_id="q-1", score=1.0),
        _make_attempt(question_id="q-2", score=0.5),
    ]
    prof = MasteryEngine.compute_objective_mastery(lo, attempts=atts)

    assert prof.mastery_state == MasteryState.DEVELOPING
    assert prof.performance_score == 0.75
    assert prof.confidence_score == 0.6667
    assert prof.distinct_questions_attempted == 2


@pytest.mark.unit
def test_mastery_mastered_state() -> None:
    lo = LearningObjective(
        id="lo-1",
        topic_id="t-1",
        code="LO_BCNF",
        title="BCNF",
        description="",
        order_index=1,
        prerequisite_objective_ids=[],
    )
    # 3 distinct questions, all 1.0 -> P = 1.0, C = 1.0 -> MASTERED
    atts = [
        _make_attempt(question_id="q-1", score=1.0),
        _make_attempt(question_id="q-2", score=1.0),
        _make_attempt(question_id="q-3", score=1.0),
    ]
    prof = MasteryEngine.compute_objective_mastery(lo, attempts=atts)

    assert prof.mastery_state == MasteryState.MASTERED
    assert prof.performance_score == 1.0
    assert prof.confidence_score == 1.0


@pytest.mark.unit
def test_mastery_needs_remediation() -> None:
    lo = LearningObjective(
        id="lo-1",
        topic_id="t-1",
        code="LO_MINIMAL_COVER",
        title="Minimal Cover",
        description="",
        order_index=1,
        prerequisite_objective_ids=[],
    )
    # 3 distinct questions, all 0.0 -> P = 0.0, C = 1.0 -> NEEDS_REMEDIATION
    atts = [
        _make_attempt(question_id="q-1", score=0.0),
        _make_attempt(question_id="q-2", score=0.0),
        _make_attempt(question_id="q-3", score=0.0),
    ]
    prof = MasteryEngine.compute_objective_mastery(lo, attempts=atts)

    assert prof.mastery_state == MasteryState.NEEDS_REMEDIATION
    assert prof.performance_score == 0.0
    assert prof.confidence_score == 1.0


@pytest.mark.unit
def test_mastery_rule3_non_duplicate_evidence() -> None:
    lo = LearningObjective(
        id="lo-1",
        topic_id="t-1",
        code="LO_CLOSURE",
        title="Closure",
        description="",
        order_index=1,
        prerequisite_objective_ids=[],
    )
    # 5 attempts on the EXACT SAME question_id 'q-1'
    atts = [_make_attempt(question_id="q-1", score=1.0) for _ in range(5)]
    prof = MasteryEngine.compute_objective_mastery(lo, attempts=atts)

    # Distinct question count is 1, so confidence cannot exceed 1/3 (0.33)
    assert prof.distinct_questions_attempted == 1
    assert prof.total_attempts == 5
    assert prof.confidence_score == 0.3333
    assert prof.mastery_state == MasteryState.INSUFFICIENT_EVIDENCE


@pytest.mark.unit
def test_mastery_rule4_hint_degradation() -> None:
    lo = LearningObjective(
        id="lo-1",
        topic_id="t-1",
        code="LO_KEYS",
        title="Keys",
        description="",
        order_index=1,
        prerequisite_objective_ids=[],
    )
    # 3 distinct questions, but all attempted with hints
    atts = [
        _make_attempt(question_id="q-1", score=0.75, is_hint_assisted=True, hint_count=1),
        _make_attempt(question_id="q-2", score=0.75, is_hint_assisted=True, hint_count=1),
        _make_attempt(question_id="q-3", score=0.75, is_hint_assisted=True, hint_count=1),
    ]
    prof = MasteryEngine.compute_objective_mastery(lo, attempts=atts)

    # Evidence weight for each is discounted (0.35 * 3 = 1.05 / 3.0 = 0.35 confidence)
    assert prof.confidence_score == 0.35
    assert prof.mastery_state == MasteryState.INSUFFICIENT_EVIDENCE


@pytest.mark.unit
def test_mastery_rule5_hypothetical_prerequisites() -> None:
    lo_child = LearningObjective(
        id="lo-child",
        topic_id="t-1",
        code="LO_CHILD",
        title="Child",
        description="",
        order_index=2,
        prerequisite_objective_ids=["LO_PARENT"],
    )
    # Child has 3 perfect attempts
    atts = [
        _make_attempt(question_id="q-1", score=1.0),
        _make_attempt(question_id="q-2", score=1.0),
        _make_attempt(question_id="q-3", score=1.0),
    ]

    # Case A: Parent is in NEEDS_REMEDIATION
    parent_prof_bad = ObjectiveMasteryProfile(
        objective_id="lo-parent",
        objective_code="LO_PARENT",
        performance_score=0.2,
        confidence_score=1.0,
        mastery_state=MasteryState.NEEDS_REMEDIATION,
        prerequisites_satisfied=True,
    )
    prof_blocked = MasteryEngine.compute_objective_mastery(
        lo_child, attempts=atts, prerequisite_profiles={"LO_PARENT": parent_prof_bad}
    )
    assert prof_blocked.prerequisites_satisfied is False
    assert "LO_PARENT" in prof_blocked.blocked_by_prerequisites

    # Case B: Parent is MASTERED
    parent_prof_good = ObjectiveMasteryProfile(
        objective_id="lo-parent",
        objective_code="LO_PARENT",
        performance_score=1.0,
        confidence_score=1.0,
        mastery_state=MasteryState.MASTERED,
        prerequisites_satisfied=True,
    )
    prof_satisfied = MasteryEngine.compute_objective_mastery(
        lo_child, attempts=atts, prerequisite_profiles={"LO_PARENT": parent_prof_good}
    )
    assert prof_satisfied.prerequisites_satisfied is True
    assert len(prof_satisfied.blocked_by_prerequisites) == 0
