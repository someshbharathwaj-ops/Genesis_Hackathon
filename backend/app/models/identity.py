"""Identity, user, course, and enrollment models."""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.curriculum import Topic


class UserRole(str, enum.Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class User(Base, UUIDMixin, TimestampMixin):
    """User account entity representing students, instructors, or administrators."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),
        default=UserRole.STUDENT,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    enrollments: Mapped[list["CourseEnrollment"]] = relationship(
        "CourseEnrollment",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    attempts: Mapped[list["Attempt"]] = relationship(
        "Attempt",
        back_populates="student",
        cascade="all, delete-orphan",
    )


class Course(Base, UUIDMixin, TimestampMixin):
    """Course catalog entity."""

    __tablename__ = "courses"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    instructor_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    enrollments: Mapped[list["CourseEnrollment"]] = relationship(
        "CourseEnrollment",
        back_populates="course",
        cascade="all, delete-orphan",
    )
    topics: Mapped[list["Topic"]] = relationship(
        "Topic",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Topic.order_index",
    )


class CourseEnrollment(Base, UUIDMixin, TimestampMixin):
    """Student enrollment in an active course."""

    __tablename__ = "course_enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_user_course_enrollment"),)

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="enrollments")
    course: Mapped["Course"] = relationship("Course", back_populates="enrollments")
