"""Unit tests for Evidence Representation and Bounded Diagnosis Engine."""

from datetime import UTC, datetime

from app.models.attempt import AssessmentContext, Attempt, AttemptStatus
from app.models.curriculum import LearningObjective
from app.modules.adaptive_learning.diagnosis_engine import (
    BoundedDiagnosisEngine,
    DiagnosticAction,
    DiagnosticStatus,
    EvidenceValidity,
    MisconceptionStatus,
    SufficiencyStatus,
)


def _make_mock_attempt(
    attempt_id: str,
    question_id: str,
    score: float,
    max_score: float = 1.0,
    is_hint: bool = False,
    hint_count: int = 0,
    context: AssessmentContext = AssessmentContext.DIAGNOSTIC,
    deductions: list[dict] | None = None,
) -> Attempt:
    is_correct = score >= max_score
    deductions = deductions or []
    return Attempt(
        id=attempt_id,
        idempotency_key=f"idem_{attempt_id}",
        student_id="student_1",
        question_id=question_id,
        question_version_id="ver_1",
        assessment_context=context,
        submitted_answer={"val": "test"},
        is_hint_assisted=is_hint,
        hint_count=hint_count,
        time_spent_ms=15000,
        submitted_at=datetime.now(UTC),
        status=AttemptStatus.GRADED,
        is_correct=is_correct,
        score_achieved=score,
        max_possible_score=max_score,
        grading_provenance={
            "evaluator": "DBMSDeterministicGrader",
            "deductions": deductions,
        },
    )


def test_single_failure_does_not_declare_weakness_or_confirmed_misconception() -> None:
    """Rule 2: Non-Catastrophic Diagnosis - a single failed item must NEVER declare

    systemic weakness or a confirmed misconception.
    """
    objective = LearningObjective(
        id="lo_1",
        topic_id="top_1",
        code="LO_CLOSURE",
        title="Attribute Closure",
        description="Compute closure",
        order_index=1,
        prerequisite_objective_ids=[],
    )

    # Student fails a single question
    attempt = _make_mock_attempt(
        attempt_id="att_1",
        question_id="q_1",
        score=0.0,
        deductions=[{"reason": "Missing attributes in closure", "attributes": ["B", "C"]}],
    )

    outcome = BoundedDiagnosisEngine.evaluate_diagnosis(
        objective=objective,
        attempts=[attempt],
    )

    # Must be INSUFFICIENT_EVIDENCE, NOT demonstrated_weakness
    assert outcome.diagnostic_status == DiagnosticStatus.INSUFFICIENT_EVIDENCE
    assert outcome.sufficiency_status == SufficiencyStatus.INSUFFICIENT
    assert outcome.confidence_score < 0.50

    # The error signature must be a CANDIDATE signal, NOT confirmed
    assert len(outcome.confirmed_misconceptions) == 0
    assert len(outcome.candidate_signals) == 1
    assert outcome.candidate_signals[0].status == MisconceptionStatus.CANDIDATE_SIGNAL
    assert outcome.candidate_signals[0].signature == "Missing attributes in closure"

    # Recommended action is a diagnostic probe, not deep remediation
    assert outcome.recommended_action == DiagnosticAction.RECOMMEND_DIAGNOSTIC_PROBE


def test_confirmed_misconception_requires_multiple_distinct_observations() -> None:
    """Rule 2: Error patterns become confirmed misconceptions only when observed

    across >= 2 distinct items.
    """
    objective = LearningObjective(
        id="lo_1",
        topic_id="top_1",
        code="LO_CLOSURE",
        title="Attribute Closure",
        description="Compute closure",
        order_index=1,
        prerequisite_objective_ids=[],
    )

    att_1 = _make_mock_attempt(
        attempt_id="att_1",
        question_id="q_1",
        score=0.0,
        deductions=[{"reason": "Missing attributes in closure", "attributes": ["B"]}],
    )
    att_2 = _make_mock_attempt(
        attempt_id="att_2",
        question_id="q_2",
        score=0.0,
        deductions=[{"reason": "Missing attributes in closure", "attributes": ["C"]}],
    )

    outcome = BoundedDiagnosisEngine.evaluate_diagnosis(
        objective=objective,
        attempts=[att_1, att_2],
    )

    # Now observed across 2 distinct questions
    assert len(outcome.confirmed_misconceptions) == 1
    assert outcome.confirmed_misconceptions[0].status == MisconceptionStatus.CONFIRMED_MISCONCEPTION
    assert outcome.confirmed_misconceptions[0].occurrence_count == 2
    assert len(outcome.candidate_signals) == 0


def test_demonstrated_weakness_on_sufficient_evidence() -> None:
    """Demonstrated weakness requires sufficient evidence (C_k >= 0.50 and distinct questions)."""
    objective = LearningObjective(
        id="lo_1",
        topic_id="top_1",
        code="LO_KEYS",
        title="Candidate Keys",
        description="Derive candidate keys",
        order_index=1,
        prerequisite_objective_ids=[],
    )

    # 2 distinct unassisted failures gives weight = 2.0 -> C_k = 2.0 / 3.0 = 0.67 >= 0.50
    att_1 = _make_mock_attempt("att_1", "q_1", score=0.0)
    att_2 = _make_mock_attempt("att_2", "q_2", score=0.2)

    outcome = BoundedDiagnosisEngine.evaluate_diagnosis(
        objective=objective,
        attempts=[att_1, att_2],
    )

    assert outcome.sufficiency_status == SufficiencyStatus.SUFFICIENT
    assert outcome.confidence_score >= 0.50
    assert outcome.performance_score < 0.60
    assert outcome.diagnostic_status == DiagnosticStatus.DEMONSTRATED_WEAKNESS


def test_rule_3_non_duplicate_evidence_discounting() -> None:
    """Rule 3: Repeated attempts on identical question ID do not grant fresh independent weight."""
    objective = LearningObjective(
        id="lo_1",
        topic_id="top_1",
        code="LO_KEYS",
        title="Candidate Keys",
        description="Derive keys",
        order_index=1,
        prerequisite_objective_ids=[],
    )

    # 3 attempts on the exact same question q_1
    att_1 = _make_mock_attempt("att_1", "q_1", score=0.0)
    att_2 = _make_mock_attempt("att_2", "q_1", score=0.5)
    att_3 = _make_mock_attempt("att_3", "q_1", score=1.0)

    ledger = BoundedDiagnosisEngine.compile_evidence_ledger(objective.id, [att_1, att_2, att_3])

    assert ledger.total_attempts == 3
    assert ledger.distinct_questions_count == 1
    assert ledger.repetition_count == 2
    # Only the first attempt granted weight (1.0)
    assert ledger.total_evidence_weight == 1.0
    # Because distinct questions < 2 and C_k = 1/3 = 0.33, sufficiency is INSUFFICIENT
    assert ledger.sufficiency_status == SufficiencyStatus.INSUFFICIENT


def test_rule_4_hint_degradation() -> None:
    """Rule 4: Hint-assisted attempts have degraded evidence weight (Whint <= 0.35)."""
    objective = LearningObjective(
        id="lo_1",
        topic_id="top_1",
        code="LO_MINIMAL_COVER",
        title="Minimal Cover",
        description="Compute minimal cover",
        order_index=1,
        prerequisite_objective_ids=[],
    )

    att = _make_mock_attempt("att_1", "q_1", score=1.0, is_hint=True, hint_count=2)
    ledger = BoundedDiagnosisEngine.compile_evidence_ledger(objective.id, [att])

    assert ledger.hint_assisted_count == 1
    assert ledger.valid_independent_count == 0
    assert ledger.total_evidence_weight == 0.35
    assert ledger.items[0].validity == EvidenceValidity.HINT_DEGRADED
    assert ledger.items[0].effective_weight == 0.35


def test_rule_5_hypothetical_prerequisites_root_cause_attribution() -> None:
    """Rule 5: Child weakness correlates with prerequisite deficit when prerequisite is weak,

    and isolates strictly to child when prerequisites are mastered.
    Child failure NEVER fails parent prerequisite.
    """
    prereq_lo = LearningObjective(
        id="lo_prereq",
        topic_id="top_1",
        code="LO_CLOSURE",
        title="Closure",
        description="Closure",
        order_index=1,
        prerequisite_objective_ids=[],
    )
    child_lo = LearningObjective(
        id="lo_child",
        topic_id="top_1",
        code="LO_KEYS",
        title="Candidate Keys",
        description="Keys",
        order_index=2,
        prerequisite_objective_ids=["LO_CLOSURE"],
    )

    # Case A: Prerequisite is weak
    prereq_diag_weak = BoundedDiagnosisEngine.evaluate_diagnosis(
        objective=prereq_lo,
        attempts=[
            _make_mock_attempt("a1", "q_c1", score=0.0),
            _make_mock_attempt("a2", "q_c2", score=0.0),
        ],
    )
    assert prereq_diag_weak.diagnostic_status == DiagnosticStatus.DEMONSTRATED_WEAKNESS

    child_diag_a = BoundedDiagnosisEngine.evaluate_diagnosis(
        objective=child_lo,
        attempts=[
            _make_mock_attempt("a3", "q_k1", score=0.0),
            _make_mock_attempt("a4", "q_k2", score=0.0),
        ],
        prerequisite_diagnoses={"LO_CLOSURE": prereq_diag_weak},
    )
    assert not child_diag_a.prerequisites_satisfied
    assert "PREREQUISITE_HYPOTHESIS_DEFICIT" in str(child_diag_a.root_cause_attribution)
    assert child_diag_a.recommended_action == DiagnosticAction.RECOMMEND_PREREQUISITE_REMEDIATION

    # Case B: Prerequisite is mastered
    prereq_diag_mastered = BoundedDiagnosisEngine.evaluate_diagnosis(
        objective=prereq_lo,
        attempts=[
            _make_mock_attempt("a1", "q_c1", score=1.0),
            _make_mock_attempt("a2", "q_c2", score=1.0),
            _make_mock_attempt("a5", "q_c3", score=1.0),
        ],
    )
    assert prereq_diag_mastered.diagnostic_status == DiagnosticStatus.MASTERED

    child_diag_b = BoundedDiagnosisEngine.evaluate_diagnosis(
        objective=child_lo,
        attempts=[
            _make_mock_attempt("a3", "q_k1", score=0.0),
            _make_mock_attempt("a4", "q_k2", score=0.0),
        ],
        prerequisite_diagnoses={"LO_CLOSURE": prereq_diag_mastered},
    )
    assert child_diag_b.prerequisites_satisfied
    assert "ISOLATED_CONCEPT_GAP" in str(child_diag_b.root_cause_attribution)
    # Prerequisite remains mastered even though child failed
    assert prereq_diag_mastered.diagnostic_status == DiagnosticStatus.MASTERED


def test_conflicting_evidence_detection() -> None:
    """Stark variance between distinct independent questions triggers CONFLICTING_EVIDENCE."""
    objective = LearningObjective(
        id="lo_1",
        topic_id="top_1",
        code="LO_NF",
        title="Normal Forms",
        description="Normal forms",
        order_index=1,
        prerequisite_objective_ids=[],
    )

    # Student scores 0.0 on q_1 and 1.0 on q_2
    att_1 = _make_mock_attempt("att_1", "q_1", score=0.0)
    att_2 = _make_mock_attempt("att_2", "q_2", score=1.0)

    outcome = BoundedDiagnosisEngine.evaluate_diagnosis(
        objective=objective,
        attempts=[att_1, att_2],
    )

    assert outcome.evidence_ledger.is_conflicting
    assert outcome.diagnostic_status == DiagnosticStatus.CONFLICTING_EVIDENCE
    assert outcome.recommended_action == DiagnosticAction.RECOMMEND_DIAGNOSTIC_PROBE


def test_recovery_routing_on_persistent_failure() -> None:
    """Rule 7: Persistent failure (>= 4 failed attempts) routes to GROUNDED_REVISION

    to prevent exhaustion.
    """
    objective = LearningObjective(
        id="lo_1",
        topic_id="top_1",
        code="LO_DECOMP",
        title="Decomposition",
        description="Decomposition",
        order_index=1,
        prerequisite_objective_ids=[],
    )

    attempts = [_make_mock_attempt(f"att_{i}", f"q_{i}", score=0.1) for i in range(1, 5)]

    outcome = BoundedDiagnosisEngine.evaluate_diagnosis(
        objective=objective,
        attempts=attempts,
    )

    assert outcome.recommended_action == DiagnosticAction.GROUNDED_REVISION
    assert any("Recovery Routing" in r for r in outcome.applied_rules)
