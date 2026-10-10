"""Immutable Attempt, grading provenance, and Idempotency models."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.identity import User
    from app.models.question import Question, QuestionVersion


class AttemptStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    GRADED = "graded"
    REGRADED = "regraded"
    REJECTED_BY_STUDENT = "rejected_by_student"


class AssessmentContext(str, enum.Enum):
    DIAGNOSTIC = "diagnostic"
    INDEPENDENT_CHECKPOINT = "independent_checkpoint"
    UNSCORED_PRACTICE = "unscored_practice"
    RETENTION_REVIEW = "retention_review"


class Attempt(Base, UUIDMixin, TimestampMixin):
    """Immutable record of an individual question attempt and its grading provenance."""

    __tablename__ = "attempts"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_attempt_idempotency_key"),
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    student_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("question_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assessment_context: Mapped[AssessmentContext] = mapped_column(
        SQLEnum(AssessmentContext),
        default=AssessmentContext.DIAGNOSTIC,
        nullable=False,
    )

    # Submission payload
    submitted_answer: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_hint_assisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hint_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timings (ms)
    time_spent_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Deterministic grading outcomes
    status: Mapped[AttemptStatus] = mapped_column(
        SQLEnum(AttemptStatus),
        default=AttemptStatus.GRADED,
        nullable=False,
    )
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score_achieved: Mapped[float] = mapped_column(Float, nullable=False)
    max_possible_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Immutable provenance capturing exact rubric rule evaluations
    grading_provenance: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="Detailed breakdown of deterministic rubric checks and deductions",
    )

    # In case of manual re-evaluations, parent attempt link preserves original audit trail
    parent_attempt_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("attempts.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    student: Mapped["User"] = relationship("User", back_populates="attempts")
    question: Mapped["Question"] = relationship("Question", back_populates="attempts")
    question_version: Mapped["QuestionVersion"] = relationship(
        "QuestionVersion",
        back_populates="attempts",
    )


class IdempotencyRecord(Base, UUIDMixin, TimestampMixin):
    """Storage for idempotency keys to prevent double-submissions and race conditions."""

    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_idempotency_record_key"),
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    request_path: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 hash of the incoming request body",
    )
    response_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[str] = mapped_column(Text, nullable=False)
