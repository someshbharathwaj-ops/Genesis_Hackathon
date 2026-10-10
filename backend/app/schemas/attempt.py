"""Attempt Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.attempt import AssessmentContext, AttemptStatus


class AttemptCreate(BaseModel):
    student_id: str
    question_id: str
    submitted_answer: dict[str, Any]
    is_hint_assisted: bool = False
    hint_count: int = 0
    time_spent_ms: int = 0
    assessment_context: AssessmentContext = AssessmentContext.DIAGNOSTIC


class AttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    idempotency_key: str
    student_id: str
    question_id: str
    question_version_id: str
    assessment_context: AssessmentContext
    submitted_answer: dict[str, Any]
    is_hint_assisted: bool
    hint_count: int
    time_spent_ms: int
    submitted_at: datetime | None = None
    status: AttemptStatus
    is_correct: bool
    score_achieved: float
    max_possible_score: float
    grading_provenance: dict[str, Any]
    created_at: datetime
