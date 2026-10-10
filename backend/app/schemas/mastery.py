"""Mastery evaluation schemas for API responses."""

from typing import Any

from pydantic import BaseModel

from app.modules.adaptive_learning.mastery_engine import MasteryState


class ObjectiveMasteryResponse(BaseModel):
    objective_id: str
    objective_code: str
    performance_score: float
    confidence_score: float
    mastery_state: MasteryState
    prerequisites_satisfied: bool
    blocked_by_prerequisites: list[str]
    total_attempts: int
    distinct_questions_attempted: int
    unassisted_correct_count: int
    hint_assisted_count: int
    details: dict[str, Any] = {}


class CourseMasterySummaryResponse(BaseModel):
    student_id: str
    course_id: str
    total_objectives: int
    mastered_count: int
    developing_count: int
    needs_remediation_count: int
    untested_count: int
    average_performance: float
    average_confidence: float
    objectives: list[ObjectiveMasteryResponse]
