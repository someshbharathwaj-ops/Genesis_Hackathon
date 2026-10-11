"""Knowledge engine schema for course documents and semantic chunks.

Revision ID: 002_document_knowledge_schema
Revises: 001_initial_schema
Create Date: 2026-10-11 03:50:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002_document_knowledge_schema"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. documentstatus enum
    document_status = sa.Enum("pending", "indexed", "empty", "failed", name="documentstatus")

    # 2. course_documents table
    op.create_table(
        "course_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "course_id",
            sa.String(36),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("mime_type", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False, default=0),
        sa.Column("status", document_status, nullable=False, default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("course_id", "content_hash", name="uq_course_doc_hash"),
    )
    op.create_index("ix_course_documents_course_id", "course_documents", ["course_id"])
    op.create_index("ix_course_documents_content_hash", "course_documents", ["content_hash"])

    # 3. document_chunks table
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("course_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            sa.String(36),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, default=0),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("metadata_attributes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_course_id", "document_chunks", ["course_id"])


def downgrade() -> None:
    op.drop_index("ix_document_chunks_course_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index("ix_course_documents_content_hash", table_name="course_documents")
    op.drop_index("ix_course_documents_course_id", table_name="course_documents")
    op.drop_table("course_documents")

    op.execute("DROP TYPE IF EXISTS documentstatus")
