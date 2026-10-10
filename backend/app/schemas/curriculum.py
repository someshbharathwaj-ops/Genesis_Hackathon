"""Curriculum Topic and LearningObjective Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class LearningObjectiveCreate(BaseModel):
    code: str
    title: str
    description: str
    order_index: int = 0
    prerequisite_objective_ids: list[str] = []
    metadata_attributes: dict[str, Any] = {}


class LearningObjectiveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    topic_id: str
    code: str
    title: str
    description: str
    order_index: int
    prerequisite_objective_ids: list[str]
    metadata_attributes: dict[str, Any]
    created_at: datetime


class TopicCreate(BaseModel):
    code: str
    title: str
    description: str | None = None
    order_index: int = 0


class TopicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    code: str
    title: str
    description: str | None = None
    order_index: int
    created_at: datetime
    objectives: list[LearningObjectiveResponse] = []
