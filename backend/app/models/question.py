"""Question and QuestionVersion models ensuring immutable versioning and provenance."""

import enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.curriculum import LearningObjective


class DifficultyLevel(str, enum.Enum):
    INTRODUCTORY = "introductory"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class VerificationStatus(str, enum.Enum):
    DRAFT = "draft"
    VERIFIED = "verified"
    DEPRECATED = "deprecated"


class QuestionType(str, enum.Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    MULTIPLE_SELECT = "multiple_select"
    EXPRESSION = "expression"
    NORMALIZATION_DECOMPOSITION = "normalization_decomposition"
    MINIMAL_COVER = "minimal_cover"


class Question(Base, UUIDMixin, TimestampMixin):
    """Canonical question entity linking all historical versions."""

    __tablename__ = "questions"

    objective_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("learning_objectives.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(
        SQLEnum(QuestionType),
        default=QuestionType.MULTIPLE_CHOICE,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    objective: Mapped["LearningObjective"] = relationship(
        "LearningObjective",
        back_populates="questions",
    )
    versions: Mapped[list["QuestionVersion"]] = relationship(
        "QuestionVersion",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionVersion.version_number.desc()",
    )
    attempts: Mapped[list["Attempt"]] = relationship(
        "Attempt",
        back_populates="question",
    )


class QuestionVersion(Base, UUIDMixin, TimestampMixin):
    """Immutable snapshot of a question's prompt, answer key, rubric, and verification status."""

    __tablename__ = "question_versions"
    __table_args__ = (
        UniqueConstraint("question_id", "version_number", name="uq_question_version_number"),
    )

    question_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        SQLEnum(DifficultyLevel),
        default=DifficultyLevel.INTERMEDIATE,
        nullable=False,
    )
    max_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Deterministic answer key and grading rubric specifications
    options: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON,
        nullable=True,
        default=None,
    )
    answer_key: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    rubric: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Verification and provenance
    verification_status: Mapped[VerificationStatus] = mapped_column(
        SQLEnum(VerificationStatus),
        default=VerificationStatus.DRAFT,
        nullable=False,
        index=True,
    )
    verified_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provenance_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 hash of the canonical prompt + rubric + answer_key",
    )

    # Relationships
    question: Mapped["Question"] = relationship("Question", back_populates="versions")
    attempts: Mapped[list["Attempt"]] = relationship(
        "Attempt",
        back_populates="question_version",
    )
