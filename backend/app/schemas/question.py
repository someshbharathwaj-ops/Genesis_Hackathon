"""Question and QuestionVersion Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.question import DifficultyLevel, QuestionType, VerificationStatus


class QuestionVersionCreate(BaseModel):
    prompt: str
    difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    max_score: float = 1.0
    options: list[dict[str, Any]] | None = None
    answer_key: dict[str, Any]
    rubric: dict[str, Any]
    explanation: str | None = None
    verification_status: VerificationStatus = VerificationStatus.DRAFT
    verified_by: str | None = None


class QuestionVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    question_id: str
    version_number: int
    prompt: str
    difficulty: DifficultyLevel
    max_score: float
    options: list[dict[str, Any]] | None = None
    answer_key: dict[str, Any]
    rubric: dict[str, Any]
    explanation: str | None = None
    verification_status: VerificationStatus
    verified_by: str | None = None
    provenance_hash: str
    created_at: datetime


class QuestionCreate(BaseModel):
    objective_id: str
    title: str
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE
    initial_version: QuestionVersionCreate


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    objective_id: str
    title: str
    question_type: QuestionType
    is_active: bool
    created_at: datetime
    versions: list[QuestionVersionResponse] = []
