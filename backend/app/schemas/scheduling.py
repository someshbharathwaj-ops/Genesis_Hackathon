"""Pydantic schemas for spaced retention scheduling and review queues."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.attempt import AssessmentContext
from app.modules.adaptive_learning.mastery_engine import MasteryState
from app.modules.adaptive_learning.scheduling_engine import ReviewUrgency


class RetentionItemSchema(BaseModel):
    """Granular retention scheduling state for a single objective."""

    objective_id: str
    objective_code: str
    objective_title: str
    mastery_state: MasteryState
    performance_score: float = Field(..., ge=0.0, le=1.0)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    last_attempt_at: datetime | None = None
    elapsed_hours: float
    in_working_memory: bool
    retention_eligible: bool
    interval_days: float
    next_review_due: datetime | None = None
    retention_stability_days: float
    estimated_retention: float = Field(..., ge=0.0, le=1.0)
    urgency_score: float = Field(..., ge=0.0, le=1.0)
    urgency_classification: ReviewUrgency
    recommended_action: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewQueueResponse(BaseModel):
    """Course-level spaced review queue for a student."""

    student_id: str
    course_id: str
    as_of_time: datetime
    total_objectives_evaluated: int
    overdue_count: int
    due_count: int
    working_memory_locked_count: int
    items: list[RetentionItemSchema]


class PlanRetentionSessionRequest(BaseModel):
    """Request payload to plan a bounded retention review session."""

    max_items: int = Field(default=5, ge=1, le=10)


class RetentionSessionPlanResponse(BaseModel):
    """Ready-to-execute spaced retention review session plan."""

    student_id: str
    course_id: str
    as_of_time: datetime
    context: AssessmentContext = AssessmentContext.RETENTION_REVIEW
    total_items: int
    reason: str
    planned_items: list[RetentionItemSchema]
