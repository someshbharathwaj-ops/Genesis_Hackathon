"""Pydantic schemas for scheduled assessments and in-app notifications."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ScheduledAssessmentCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str = Field(default="")
    scheduled_at: datetime
    duration_minutes: int = Field(default=30, ge=5, le=180)
    target_objective_id: str | None = None


class ScheduledAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    created_by_id: str
    title: str
    description: str
    scheduled_at: datetime
    duration_minutes: int
    target_objective_id: str | None
    status: str
    created_at: datetime | None = None


class InAppNotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    course_id: str
    assessment_id: str | None
    title: str
    message: str
    is_read: bool
    notification_type: str
    created_at: datetime | None = None
