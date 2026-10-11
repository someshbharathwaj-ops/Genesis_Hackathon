"""initial schema for identity, curriculum, questions, attempts, and idempotency

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-10-10 17:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("student", "instructor", "admin", name="userrole"),
            nullable=False,
            default="student",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_id", "users", ["id"])

    # 2. courses
    op.create_table(
        "courses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1024), nullable=True),
        sa.Column(
            "instructor_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_courses_code", "courses", ["code"])
    op.create_index("ix_courses_id", "courses", ["id"])

    # 3. course_enrollments
    op.create_table(
        "course_enrollments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "course_id",
            sa.String(36),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "course_id", name="uq_user_course_enrollment"),
    )
    op.create_index("ix_course_enrollments_user_id", "course_enrollments", ["user_id"])
    op.create_index("ix_course_enrollments_course_id", "course_enrollments", ["course_id"])

    # 4. topics
    op.create_table(
        "topics",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "course_id",
            sa.String(36),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1024), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("course_id", "code", name="uq_topic_course_code"),
    )
    op.create_index("ix_topics_course_id", "topics", ["course_id"])

    # 5. learning_objectives
    op.create_table(
        "learning_objectives",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "topic_id",
            sa.String(36),
            sa.ForeignKey("topics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.String(1024), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, default=0),
        sa.Column("prerequisite_objective_ids", sa.JSON(), nullable=False, default=list),
        sa.Column("metadata_attributes", sa.JSON(), nullable=False, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("topic_id", "code", name="uq_lo_topic_code"),
    )
    op.create_index("ix_learning_objectives_topic_id", "learning_objectives", ["topic_id"])

    # 6. questions
    op.create_table(
        "questions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "objective_id",
            sa.String(36),
            sa.ForeignKey("learning_objectives.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column(
            "question_type",
            sa.Enum(
                "multiple_choice",
                "multiple_select",
                "expression",
                "normalization_decomposition",
                "minimal_cover",
                name="questiontype",
            ),
            nullable=False,
            default="multiple_choice",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_questions_objective_id", "questions", ["objective_id"])

    # 7. question_versions
    op.create_table(
        "question_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "question_id",
            sa.String(36),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False, default=1),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column(
            "difficulty",
            sa.Enum("introductory", "intermediate", "advanced", name="difficultylevel"),
            nullable=False,
            default="intermediate",
        ),
        sa.Column("max_score", sa.Float(), nullable=False, default=1.0),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("answer_key", sa.JSON(), nullable=False),
        sa.Column("rubric", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column(
            "verification_status",
            sa.Enum("draft", "verified", "deprecated", name="verificationstatus"),
            nullable=False,
            default="draft",
        ),
        sa.Column("verified_by", sa.String(255), nullable=True),
        sa.Column("provenance_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("question_id", "version_number", name="uq_question_version_number"),
    )
    op.create_index("ix_question_versions_question_id", "question_versions", ["question_id"])
    op.create_index(
        "ix_question_versions_verification_status", "question_versions", ["verification_status"]
    )

    # 8. attempts
    op.create_table(
        "attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("idempotency_key", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "student_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.String(36),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_version_id",
            sa.String(36),
            sa.ForeignKey("question_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "assessment_context",
            sa.Enum(
                "diagnostic",
                "independent_checkpoint",
                "unscored_practice",
                "retention_review",
                name="assessmentcontext",
            ),
            nullable=False,
            default="diagnostic",
        ),
        sa.Column("submitted_answer", sa.JSON(), nullable=False),
        sa.Column("is_hint_assisted", sa.Boolean(), nullable=False, default=False),
        sa.Column("hint_count", sa.Integer(), nullable=False, default=0),
        sa.Column("time_spent_ms", sa.Integer(), nullable=False, default=0),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "in_progress", "graded", "regraded", "rejected_by_student", name="attemptstatus"
            ),
            nullable=False,
            default="graded",
        ),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("score_achieved", sa.Float(), nullable=False),
        sa.Column("max_possible_score", sa.Float(), nullable=False),
        sa.Column("grading_provenance", sa.JSON(), nullable=False),
        sa.Column(
            "parent_attempt_id",
            sa.String(36),
            sa.ForeignKey("attempts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_attempts_idempotency_key", "attempts", ["idempotency_key"])
    op.create_index("ix_attempts_student_id", "attempts", ["student_id"])
    op.create_index("ix_attempts_question_id", "attempts", ["question_id"])
    op.create_index("ix_attempts_question_version_id", "attempts", ["question_version_id"])

    # 9. idempotency_records
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("idempotency_key", sa.String(64), nullable=False, unique=True),
        sa.Column("request_path", sa.String(255), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_idempotency_records_key", "idempotency_records", ["idempotency_key"])


def downgrade() -> None:
    op.drop_table("idempotency_records")
    op.drop_table("attempts")
    op.drop_table("question_versions")
    op.drop_table("questions")
    op.drop_table("learning_objectives")
    op.drop_table("topics")
    op.drop_table("course_enrollments")
    op.drop_table("courses")
    op.drop_table("users")
