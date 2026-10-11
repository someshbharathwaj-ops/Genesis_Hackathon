"""Pydantic schemas for Grounded Revisor evidence review and adversarial audit."""

from typing import Any

from pydantic import BaseModel, Field

from app.modules.ai_engine.revisor_engine import GroundedAuditStatus


class RevisorReviewRequest(BaseModel):
    """Request payload to audit a candidate pedagogical statement or student explanation."""

    student_id: str
    candidate_text: str = Field(
        ...,
        min_length=5,
        max_length=10000,
        description="Candidate explanation, response, or misconception claim to audit.",
    )
    query_or_topic: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="The subject or topic query to retrieve course evidence for.",
    )
    objective_id: str | None = Field(
        default=None,
        description="Optional learning objective ID to scope the review.",
    )
    check_deterministic_logic: bool = Field(
        default=True,
        description="Whether to run deterministic domain validation (e.g. relational closures).",
    )


class RevisorReviewResponse(BaseModel):
    """Structured audit outcome from the Grounded Revisor."""

    course_id: str
    student_id: str
    audit_status: GroundedAuditStatus
    is_approved: bool
    summary: str
    verified_points: list[str]
    flagged_issues: list[str]
    suggested_revision: str | None = None
    citations_verified: list[str]
    abstention_recommended: bool
    model_used: str
    is_mock: bool
    retrieved_chunks_count: int
    deterministic_validation: dict[str, Any] = Field(default_factory=dict)
    warning: str | None = None
