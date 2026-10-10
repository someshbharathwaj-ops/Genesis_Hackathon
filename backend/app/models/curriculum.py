"""Curriculum hierarchy: Topic and LearningObjective models."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.identity import Course
    from app.models.question import Question


class Topic(Base, UUIDMixin, TimestampMixin):
    """Subject matter topic within a course."""

    __tablename__ = "topics"
    __table_args__ = (
        UniqueConstraint("course_id", "code", name="uq_topic_course_code"),
    )

    course_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="topics")
    objectives: Mapped[list["LearningObjective"]] = relationship(
        "LearningObjective",
        back_populates="topic",
        cascade="all, delete-orphan",
        order_by="LearningObjective.order_index",
        lazy="selectin",
    )


class LearningObjective(Base, UUIDMixin, TimestampMixin):
    """Granular learning objective within a topic."""

    __tablename__ = "learning_objectives"
    __table_args__ = (
        UniqueConstraint("topic_id", "code", name="uq_lo_topic_code"),
    )

    topic_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1024), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Prerequisite hypothesis edges: list of objective IDs that form pedagogical prerequisites
    # Note: Evaluated as reviewed hypotheses, not causal certainties
    prerequisite_objective_ids: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    metadata_attributes: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    # Relationships
    topic: Mapped["Topic"] = relationship("Topic", back_populates="objectives")
    questions: Mapped[list["Question"]] = relationship(
        "Question",
        back_populates="objective",
        cascade="all, delete-orphan",
    )
