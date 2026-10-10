"""Pydantic schemas for Course Documents and Knowledge Retrieval API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentStatus


class DocumentChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    course_id: str
    chunk_index: int
    page_number: int
    content: str
    token_count: int
    metadata_attributes: dict[str, Any] = {}
    created_at: datetime


class CourseDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    filename: str
    content_hash: str
    mime_type: str
    file_size_bytes: int
    page_count: int
    status: DocumentStatus
    error_message: str | None = None
    chunk_count: int = 0
    created_at: datetime


class CourseDocumentDetailResponse(CourseDocumentResponse):
    chunks: list[DocumentChunkResponse] = []


class RetrievalQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000, description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Max matches to return")
    similarity_threshold: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Cosine similarity cutoff below which matches are omitted",
    )


class RetrievalMatchResponse(BaseModel):
    chunk_id: str
    document_id: str
    document_filename: str
    page_number: int
    content: str
    similarity_score: float
    citation: str
    metadata_attributes: dict[str, Any] = {}


class RetrievalResponse(BaseModel):
    query: str
    course_id: str
    total_candidates: int
    matches: list[RetrievalMatchResponse]
    abstention_recommended: bool
    explanation: str
