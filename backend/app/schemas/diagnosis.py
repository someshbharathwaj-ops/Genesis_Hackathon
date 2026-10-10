"""Pydantic schemas for Evidence and Bounded Diagnosis API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.attempt import AssessmentContext
from app.modules.adaptive_learning.diagnosis_engine import (
    DiagnosticAction,
    DiagnosticStatus,
    EvidenceValidity,
    MisconceptionStatus,
    SufficiencyStatus,
)


class EvidenceItemResponse(BaseModel):
    attempt_id: str
    question_id: str
    assessment_context: AssessmentContext
    score_ratio: float
    is_correct: bool
    is_hint_assisted: bool
    hint_count: int
    repetition_index: int
    effective_weight: float
    validity: EvidenceValidity
    deductions: list[dict[str, Any]]
    submitted_at: datetime | None = None


class EvidenceLedgerResponse(BaseModel):
    objective_id: str
    total_attempts: int
    valid_independent_count: int
    hint_assisted_count: int
    repetition_count: int
    distinct_questions_count: int
    total_evidence_weight: float
    performance_score: float
    confidence_score: float
    sufficiency_status: SufficiencyStatus
    is_conflicting: bool
    conflict_reasons: list[str]
    items: list[EvidenceItemResponse] = []


class MisconceptionResponse(BaseModel):
    signature: str
    description: str
    occurrence_count: int
    status: MisconceptionStatus
    distinct_questions: list[str]
    sample_deduction: dict[str, Any]


class PrerequisiteTraceResponse(BaseModel):
    prerequisite_ref: str
    prerequisite_id: str | None = None
    prerequisite_code: str | None = None
    diagnostic_status: DiagnosticStatus
    confidence_score: float
    is_satisfied: bool
    gap_hypothesis: str | None = None


class ObjectiveDiagnosticResponse(BaseModel):
    objective_id: str
    objective_code: str
    diagnostic_status: DiagnosticStatus
    performance_score: float
    confidence_score: float
    sufficiency_status: SufficiencyStatus
    evidence_ledger: EvidenceLedgerResponse
    confirmed_misconceptions: list[MisconceptionResponse]
    candidate_signals: list[MisconceptionResponse]
    prerequisites_satisfied: bool
    prerequisite_traces: list[PrerequisiteTraceResponse]
    root_cause_attribution: str | None = None
    recommended_action: DiagnosticAction
    applied_rules: list[str]
    traceable_rationale: str


class CourseDiagnosticSummaryResponse(BaseModel):
    student_id: str
    course_id: str
    total_objectives: int
    mastered_count: int
    developing_count: int
    demonstrated_weakness_count: int
    insufficient_evidence_count: int
    untested_count: int
    conflicting_count: int
    average_performance: float
    average_confidence: float
    identified_root_cause_gaps: list[str]
    objectives: list[ObjectiveDiagnosticResponse]


class RecommendedQuestionItem(BaseModel):
    question_id: str
    title: str
    objective_id: str
    objective_code: str
    difficulty: str
    priority_reason: str


class DiagnosticSessionPlanRequest(BaseModel):
    student_id: str
    course_id: str
    target_objective_id: str | None = None


class DiagnosticSessionPlanResponse(BaseModel):
    student_id: str
    course_id: str
    target_objective_id: str | None = None
    max_session_questions: int = Field(default=5, description="Strict session budget ceiling")
    recommended_questions: list[RecommendedQuestionItem]
    session_rationale: str
